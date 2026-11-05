import logging
import os
import secrets
from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db
from .device import FixtureDeviceAdapter, InvalidDevicePayload, demo_release_payload, load_device_adapter
from .matching import MatchingUnavailable, select_match
from .schemas import ReleaseResult, StandbyRequestInput, StandbyRequestStatus, VenueInfo
from .venues import current_venue

# Fail at startup if MARKETPLACE_VENUE names an unknown venue.
current_venue()

app = FastAPI(title="Meeting Room Marketplace API")
logger = logging.getLogger(__name__)
device_bearer = HTTPBearer(auto_error=False)


@app.exception_handler(psycopg.Error)
async def database_unavailable(_request: Request, error: psycopg.Error) -> JSONResponse:
    logger.warning("Marketplace database error: %s", type(error).__name__)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


def request_status(request_id: str) -> dict:
    status = db.get_request(request_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Standby request not found")
    return status


def match_request(request_id: str) -> None:
    try:
        request = db.get_request(request_id)
        if request is None or request["status"] != "waiting":
            return
        previous_candidates = []
        for _ in range(2):
            candidates = db.list_candidates(request_id)
            if not candidates or candidates == previous_candidates:
                return
            decision = select_match(request, candidates)
            if decision is None:
                return
            if not 0 <= decision.candidate_index < len(candidates):
                logger.warning("Room matching returned an invalid candidate index")
                return
            offer = db.create_offer(
                request_id, candidates[decision.candidate_index], decision.reason, decision.provider
            )
            if offer is not None:
                return
            # Another request may have taken the slot while the matcher was choosing.
            previous_candidates = candidates
    except (db.Conflict, db.NotFound):
        # The request or opening changed while the model was choosing a candidate.
        return
    except (MatchingUnavailable, psycopg.Error, RuntimeError) as error:
        logger.warning("Room matching unavailable: %s", type(error).__name__)


def ingest_release(event: dict | None, background_tasks: BackgroundTasks) -> dict:
    if event is None:
        return {"created": False, "reason": "Event does not release a room"}
    require_database()
    result = db.record_release(event)
    if result["created"]:
        for request_id in db.list_pending_request_ids():
            background_tasks.add_task(match_request, request_id)
    return result


def demo_enabled() -> bool:
    return os.getenv("MARKETPLACE_DEMO_MODE") == "1"


def require_database() -> None:
    if not os.getenv("DATABASE_URL"):
        raise HTTPException(status_code=503, detail="Database connection is not configured")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", responses={503: {"description": "Database unavailable"}})
def ready() -> dict[str, str]:
    require_database()
    try:
        db.check_ready()
    except (psycopg.Error, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready"}


@app.post(
    "/standby-requests",
    status_code=201,
    response_model=StandbyRequestStatus,
    dependencies=[Depends(require_database)],
)
def create_standby_request(body: StandbyRequestInput, background_tasks: BackgroundTasks) -> dict:
    request_id = db.create_request({**body.model_dump(), "venue": current_venue().id})
    status = request_status(request_id)
    background_tasks.add_task(match_request, request_id)
    return status


@app.get(
    "/standby-requests/{request_id}",
    response_model=StandbyRequestStatus,
    dependencies=[Depends(require_database)],
)
def get_standby_request(request_id: UUID, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return request_status(str(request_id))


@app.post(
    "/standby-requests/{request_id}/retry",
    response_model=StandbyRequestStatus,
    dependencies=[Depends(require_database)],
)
def retry_standby_request(request_id: UUID, background_tasks: BackgroundTasks) -> dict:
    status = request_status(str(request_id))
    if status["status"] == "waiting":
        background_tasks.add_task(match_request, str(request_id))
    return status


@app.post(
    "/standby-requests/{request_id}/offers/{offer_id}/accept",
    response_model=StandbyRequestStatus,
    responses={409: {"description": "Offer expired or no longer available"}},
    dependencies=[Depends(require_database)],
)
def accept_standby_offer(
    request_id: UUID, offer_id: UUID, background_tasks: BackgroundTasks
) -> dict | Response:
    try:
        return db.accept_offer(str(request_id), str(offer_id))
    except db.NotFound as exc:
        raise HTTPException(status_code=404, detail="Standby request or offer not found") from exc
    except db.Conflict:
        background_tasks.add_task(match_request, str(request_id))
        return JSONResponse(
            status_code=409,
            content={"detail": "This offer is no longer available"},
            background=background_tasks,
        )


@app.get("/venue", response_model=VenueInfo)
def get_venue() -> dict[str, str]:
    return current_venue().public()


@app.get("/demo/config")
def demo_config() -> dict[str, bool]:
    return {"enabled": demo_enabled()}


@app.post("/demo/release", response_model=ReleaseResult)
def demo_release(background_tasks: BackgroundTasks) -> dict:
    if not demo_enabled():
        raise HTTPException(status_code=404, detail="Demo release is disabled")
    event = FixtureDeviceAdapter().normalize_release(demo_release_payload(current_venue().demo_room_id))
    return ingest_release(event, background_tasks)


@app.post("/internal/device/events", response_model=ReleaseResult)
def device_event(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(device_bearer)],
) -> dict:
    token = os.getenv("MARKETPLACE_DEVICE_TOKEN")
    if not token:
        raise HTTPException(status_code=404, detail="Device ingestion is disabled")
    if credentials is None or not secrets.compare_digest(credentials.credentials.encode(), token.encode()):
        raise HTTPException(
            status_code=401,
            detail="Invalid device credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        event = load_device_adapter().normalize_release(payload)
    except InvalidDevicePayload as exc:
        raise HTTPException(status_code=422, detail="Invalid device event") from exc
    except RuntimeError as exc:
        logger.warning("Device adapter unavailable: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Device adapter unavailable") from exc
    return ingest_release(event, background_tasks)
