import asyncio
import logging
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event, Lock
from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AwareDatetime

from . import db, host, notify, ntnu, preferences, suggestions
from .accounts import Account, require_agent_or_user, require_browser_mutation, require_user, router as accounts_router
from .device import (
    FixtureDeviceAdapter, InvalidDevicePayload, RoomRelease, RoomReleaseRequest,
    demo_release_payload, normalize_device_event,
)
from .matching import MatchingUnavailable, select_match
from .pricing import PriceQuote
from .schemas import DemoReleaseInput, ReleaseResult, Room, StandbyRequestInput, StandbyRequestStatus, VenueInfo
from .venues import current_venue

current_venue()

app = FastAPI(title="Room Marketplace API")
app.include_router(accounts_router)
app.include_router(host.router)
app.include_router(preferences.router)
app.include_router(suggestions.router)
app.include_router(notify.router)
app.include_router(ntnu.router)
logger = logging.getLogger(__name__)
device_bearer = HTTPBearer(auto_error=False)
_match_workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="room-matcher")
_match_lock = Lock()
_active_matches: dict[str, Event] = {}


_background_tasks: set[asyncio.Task] = set()


@app.on_event("startup")
async def start_notification_watch() -> None:
    task = asyncio.create_task(notify.watch_booked_empty())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@app.exception_handler(psycopg.Error)
async def database_unavailable(_request: Request, error: psycopg.Error) -> JSONResponse:
    logger.warning("Marketplace database error: %s", type(error).__name__)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


def require_renter(account: Annotated[Account, Depends(require_user)]) -> Account:
    if account.role != "renter":
        raise HTTPException(status_code=403, detail="A renter account is required")
    return account


Renter = Annotated[Account, Depends(require_renter)]


def require_standby_renter(account: Annotated[Account, Depends(require_agent_or_user)]) -> Account:
    return require_renter(account)


StandbyRenter = Annotated[Account, Depends(require_standby_renter)]


def request_status(request_id: str, account: Account) -> dict:
    status = db.get_request(request_id, user_id=account.id)
    if status is None:
        raise HTTPException(status_code=404, detail="Standby request not found")
    return status


def _match_candidates(request_id: str, previous: list[dict]) -> tuple[list[dict], bool]:
    request = db.get_request(request_id)
    if request is None or request["status"] != "waiting":
        return previous, True
    for _ in range(2):
        candidates = db.list_candidates(request_id)
        if not candidates or candidates == previous:
            return candidates, False
        previous = candidates
        decision = select_match(request, candidates)
        if decision is None:
            return previous, False
        if not 0 <= decision.candidate_index < len(candidates):
            logger.warning("Room matching returned an invalid candidate index")
            return previous, True
        offer = db.create_offer(request_id, candidates[decision.candidate_index], decision.reason, decision.provider)
        if offer is not None:
            notify.offer_created(offer["id"])
            return previous, True
        # Another request may have taken the slot while the matcher was choosing.
    return previous, False


def _claim_match(request_id: str) -> Event | None:
    with _match_lock:
        existing = _active_matches.get(request_id)
        if existing is not None:
            existing.set()
            return None
        pending = Event()
        _active_matches[request_id] = pending
        return pending


def match_request(request_id: str, pending: Event | None = None) -> None:
    # Collapse simultaneous retries into a fresh availability check, without
    # losing a release that arrived while the model was working.
    if pending is None:
        pending = _claim_match(request_id)
        if pending is None:
            return
    previous: list[dict] = []
    try:
        while True:
            pending.clear()
            previous, complete = _match_candidates(request_id, previous)
            with _match_lock:
                if complete or not pending.is_set():
                    del _active_matches[request_id]
                    return
    except (db.Conflict, db.NotFound):
        # The request or opening changed while the model was choosing a candidate.
        return
    except (MatchingUnavailable, psycopg.Error, RuntimeError) as error:
        logger.warning("Room matching unavailable: %s", type(error).__name__)
    finally:
        with _match_lock:
            if _active_matches.get(request_id) is pending:
                del _active_matches[request_id]


async def run_match_in_background(request_id: str) -> None:
    # Claim before submitting so retries also coalesce while all workers are busy.
    pending = _claim_match(request_id)
    if pending is None:
        return
    try:
        work = asyncio.get_running_loop().run_in_executor(_match_workers, match_request, request_id, pending)
    except RuntimeError:
        with _match_lock:
            del _active_matches[request_id]
        raise
    # If the HTTP task is cancelled, let the worker finish and clear its claim.
    await asyncio.shield(work)


def ingest_release(event: RoomRelease | RoomReleaseRequest | None, background_tasks: BackgroundTasks) -> dict:
    if event is None:
        return {"created": False, "reason": "Event does not release a room"}
    require_database()
    device_press = event.get("type") == "room.release_requested"
    if device_press:
        result = db.record_release_request(event)
    else:
        result = db.record_release(event)
    # The opening may have committed before a previous webhook attempt could wake the matcher.
    if result["created"] or (device_press and result.get("opening_id")):
        for request_id in db.list_pending_request_ids(event["external_room_id"]):
            background_tasks.add_task(run_match_in_background, request_id)
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


@app.get("/rooms", response_model=list[Room], dependencies=[Depends(require_database)])
def rooms() -> list[dict]:
    return db.list_rooms()


@app.get("/rooms/{room_id}", response_model=Room, dependencies=[Depends(require_database)])
def room(room_id: str) -> dict:
    listing = db.get_room(room_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return listing


@app.get("/rooms/{room_id}/quote", response_model=PriceQuote, dependencies=[Depends(require_database)])
def room_quote(
    room_id: str,
    start_at: AwareDatetime,
    duration_minutes: Annotated[int, Query(ge=1, le=720)],
    response: Response,
) -> PriceQuote:
    now = datetime.now(UTC)
    if start_at < now:
        raise HTTPException(status_code=422, detail="Choose a start time in the future")
    try:
        quote = db.get_room_quote(room_id, start_at, duration_minutes, now)
    except OverflowError as exc:
        raise HTTPException(status_code=422, detail="Start time is outside the supported date range") from exc
    if quote is None:
        raise HTTPException(status_code=404, detail="Room not found")
    response.headers["Cache-Control"] = "no-store"
    return quote


@app.get("/standby-requests", response_model=list[StandbyRequestStatus])
def standby_history(account: StandbyRenter, response: Response) -> list[dict]:
    response.headers["Cache-Control"] = "no-store"
    return db.list_requests(account.id)


@app.post(
    "/standby-requests",
    status_code=201,
    response_model=StandbyRequestStatus,
    dependencies=[Depends(require_browser_mutation)],
)
def create_standby_request(
    body: StandbyRequestInput, request: Request, background_tasks: BackgroundTasks, account: StandbyRenter,
) -> dict:
    if request.headers.get("authorization") is not None and body.auto_confirm:
        raise HTTPException(status_code=422, detail="Agent requests must set auto_confirm to false")
    data = body.model_dump()
    if data["equipment"] is None or data["max_price_ore"] is None:
        saved = preferences.load_preferences(account.id).preferences
        if data["equipment"] is None:
            data["equipment"] = saved.equipment
        if data["max_price_ore"] is None:
            if saved.max_hourly_ore is None:
                raise HTTPException(status_code=422, detail="Set a maximum price, or save one in your preferences")
            data["max_price_ore"] = min(10_000_000, (saved.max_hourly_ore * body.duration_minutes + 59) // 60)
    try:
        request_id = db.create_request(data, account.id)
    except db.NotFound as exc:
        raise HTTPException(status_code=404, detail="Room not found") from exc
    status = request_status(request_id, account)
    background_tasks.add_task(run_match_in_background, request_id)
    return status


@app.get(
    "/standby-requests/{request_id}",
    response_model=StandbyRequestStatus,
)
def get_standby_request(request_id: UUID, response: Response, account: StandbyRenter) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return request_status(str(request_id), account)


@app.post(
    "/standby-requests/{request_id}/retry",
    response_model=StandbyRequestStatus,
    dependencies=[Depends(require_browser_mutation)],
)
def retry_standby_request(
    request_id: UUID, request: Request, background_tasks: BackgroundTasks, account: StandbyRenter,
) -> dict:
    status = request_status(str(request_id), account)
    if status["status"] == "waiting":
        if status.get("auto_confirm") and request.headers.get("authorization") is not None:
            raise HTTPException(status_code=403, detail="Retry automatic bookings from your browser")
        background_tasks.add_task(run_match_in_background, str(request_id))
    return status


@app.post(
    "/standby-requests/{request_id}/offers/{offer_id}/accept",
    response_model=StandbyRequestStatus,
    responses={409: {"description": "Offer expired or no longer available"}},
    dependencies=[Depends(require_browser_mutation)],
)
def accept_standby_offer(
    request_id: UUID, offer_id: UUID, background_tasks: BackgroundTasks, account: StandbyRenter
) -> dict | Response:
    try:
        status = db.accept_offer(str(request_id), str(offer_id), user_id=account.id)
        notify.booking_confirmed(offer_id)
        return status
    except db.NotFound as exc:
        raise HTTPException(status_code=404, detail="Standby request or offer not found") from exc
    except db.Conflict:
        background_tasks.add_task(run_match_in_background, str(request_id))
        return JSONResponse(
            status_code=409,
            content={"detail": "This offer is no longer available"},
            background=background_tasks,
        )


@app.get("/demo/config")
def demo_config() -> dict[str, bool]:
    return {"enabled": demo_enabled()}


@app.get("/venue", response_model=VenueInfo)
def get_venue() -> dict[str, str]:
    return current_venue().public()


@app.post("/demo/release", response_model=ReleaseResult, dependencies=[Depends(require_browser_mutation)])
def demo_release(
    background_tasks: BackgroundTasks, _account: Renter, body: DemoReleaseInput | None = None
) -> dict:
    if not demo_enabled():
        raise HTTPException(status_code=404, detail="Demo release is disabled")
    room_id = (body.room_id if body else None) or current_venue().demo_room_id
    if db.get_room(room_id) is None:
        raise HTTPException(status_code=404, detail="Room not found")
    payload = demo_release_payload(room_id)
    event = FixtureDeviceAdapter().normalize_release(payload)
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
        event = normalize_device_event(payload)
    except InvalidDevicePayload as exc:
        raise HTTPException(status_code=422, detail="Invalid device event") from exc
    except RuntimeError as exc:
        logger.warning("Device adapter unavailable: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Device adapter unavailable") from exc
    if event is not None and event.get("type") == "room.occupancy_changed":
        require_database()
        result = db.record_occupancy(event)
        if event["occupied"] and result.get("reason") == "occupancy_recorded":
            notify.occupancy_changed(event["external_room_id"])
        return result
    return ingest_release(event, background_tasks)
