"""Device server: Atech boards post telemetry here, the marketplace reads occupancy.

The API contract lives in device/README.md.
"""

import asyncio
import logging
import secrets
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .config import load_settings
from .store import NothingToCalibrate, Store, TelemetryIn, UnknownDevice, UnknownRoom

logger = logging.getLogger("device")
bearer = HTTPBearer(auto_error=False)


def clock() -> float:
    return time.time()


async def push_outbox(app: FastAPI) -> None:
    """Send queued events to the marketplace, retrying failures with backoff."""
    store: Store = app.state.store
    settings = store.settings
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            await asyncio.sleep(1.0)
            if not settings.marketplace_url:
                continue
            headers = {"Authorization": f"Bearer {settings.marketplace_token}"} if settings.marketplace_token else {}
            for event_id, payload, attempts in store.due_events(app.state.clock()):
                try:
                    response = await client.post(
                        f"{settings.marketplace_url}/internal/device/events", json=payload, headers=headers
                    )
                    if response.is_success:
                        store.mark_sent(event_id, app.state.clock())
                        logger.info("pushed %s %s", payload["type"], payload["external_room_id"])
                    else:
                        store.mark_failed(event_id, attempts, f"HTTP {response.status_code}: {response.text}", app.state.clock())
                except httpx.HTTPError as exc:
                    store.mark_failed(event_id, attempts, f"{type(exc).__name__}: {exc}", app.state.clock())


def create_app(store: Store | None = None, *, start_push: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(push_outbox(app)) if start_push else None
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="Device server", lifespan=lifespan)
    app.state.store = store or Store(load_settings())
    app.state.clock = clock

    def get_store(request: Request) -> Store:
        return request.app.state.store

    def now(request: Request) -> float:
        return request.app.state.clock()

    def device_auth(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> None:
        token = request.app.state.store.settings.device_token
        if not token:
            return
        if credentials is None or not secrets.compare_digest(credentials.credentials.encode(), token.encode()):
            raise HTTPException(401, "Invalid device token", headers={"WWW-Authenticate": "Bearer"})

    StoreDep = Annotated[Store, Depends(get_store)]
    NowDep = Annotated[float, Depends(now)]

    class Telemetry(BaseModel):
        device_id: str = Field(min_length=1, max_length=64)
        seq: int | None = None
        uptime_ms: int | None = None
        tof_mm: list[float | None] | None = Field(default=None, min_length=64, max_length=64)
        co2_ppm: float | None = None
        temp_c: float | None = None
        rh_pct: float | None = None
        buttons: dict[str, int] = Field(default_factory=dict)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/v1/telemetry", dependencies=[Depends(device_auth)])
    def telemetry(body: Telemetry, store: StoreDep, at: NowDep) -> dict:
        try:
            room_id, occupied = store.ingest(TelemetryIn(**body.model_dump()), at)
        except UnknownDevice:
            raise HTTPException(404, f"Unknown device {body.device_id!r}; add it to DEVICES")
        return {"ok": True, "room_id": room_id, "occupied": occupied}

    @app.get("/v1/rooms")
    def rooms(store: StoreDep, at: NowDep) -> list[dict]:
        return store.rooms(at)

    @app.get("/v1/rooms/{room_id}")
    def room(room_id: str, store: StoreDep, at: NowDep) -> dict:
        try:
            return store.room(room_id, at)
        except UnknownRoom:
            raise HTTPException(404, "Unknown room")

    @app.get("/v1/rooms/{room_id}/presence")
    def presence(
        room_id: str,
        store: StoreDep,
        at: NowDep,
        start: Annotated[datetime, Query(alias="from")],
        end: Annotated[datetime, Query(alias="to")],
    ) -> dict:
        if start.utcoffset() is None or end.utcoffset() is None:
            raise HTTPException(422, "from and to must include a timezone offset")
        if end <= start:
            raise HTTPException(422, "to must be later than from")
        try:
            return store.presence(room_id, start.timestamp(), end.timestamp(), at)
        except UnknownRoom:
            raise HTTPException(404, "Unknown room")

    @app.post("/v1/rooms/{room_id}/calibrate")
    def calibrate(room_id: str, store: StoreDep, at: NowDep) -> dict:
        try:
            devices = store.calibrate(room_id, at)
        except UnknownRoom:
            raise HTTPException(404, "Unknown room")
        except NothingToCalibrate:
            raise HTTPException(409, "No online device in this room has sent a ToF frame yet")
        return {"ok": True, "room_id": room_id, "calibrated_devices": devices}

    @app.get("/v1/outbox")
    def outbox(store: StoreDep) -> list[dict]:
        """Recent events pushed (or waiting to be pushed) to the marketplace. For debugging."""
        return store.outbox()

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return DASHBOARD

    return app


DASHBOARD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Room sensors</title>
<style>
 body{font-family:system-ui,sans-serif;margin:24px;background:#0f1115;color:#e8e8e8}
 h1{font-size:18px;font-weight:600;margin:0 0 16px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
 .card{border-radius:10px;padding:16px;background:#1a1d24;border-left:6px solid #555}
 .card.free{border-color:#2fbf71}.card.busy{border-color:#e5484d}.card.off{opacity:.55}
 .state{font-size:22px;font-weight:700;margin:6px 0}
 .meta{font-size:13px;color:#a0a4ad;line-height:1.6}
</style></head><body>
<h1>Room sensors</h1><div class="grid" id="rooms"></div>
<script>
async function tick(){
  try{
    const rooms = await (await fetch('/v1/rooms')).json();
    document.getElementById('rooms').innerHTML = rooms.map(r => `
      <div class="card ${r.occupied?'busy':'free'} ${r.online?'':'off'}">
        <div class="meta">${r.room_id}</div>
        <div class="state">${r.occupied?'Occupied':'Empty'}</div>
        <div class="meta">since ${r.since ? new Date(r.since).toLocaleTimeString() : '–'}<br>
        ${r.online?'online':'offline'} · CO₂ ${r.co2_ppm ?? '–'} ppm · ${r.temp_c ?? '–'} °C</div>
      </div>`).join('');
  }catch(e){}
}
tick(); setInterval(tick, 2000);
</script></body></html>"""


app = create_app()
