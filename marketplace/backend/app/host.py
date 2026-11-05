import re
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator, model_validator

from . import db
from .accounts import Account, require_browser_mutation, require_user
from .schemas import EquipmentName, ReleaseResult, Room
from .venues import VENUES

router = APIRouter(prefix="/host", tags=["hosting"])
# Public, sign-in-free live view for the stage demo rooms only.
public_router = APIRouter(prefix="/public", tags=["public"])
LIVE_ROOM_IDS = frozenset(venue.demo_room_id for venue in VENUES.values())

RoomKind = Literal["Studio", "Workshop", "Meeting room", "Boardroom"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1800)]

_COLUMNS = "id, name, city, venue_name AS venue, kind, description, image_key, capacity, equipment, hourly_rate_ore, published"
_LIVE_STATUS = """
    (SELECT jsonb_build_object('occupied', occupied, 'changed_at', changed_at)
     FROM marketplace_room_occupancy WHERE room_id = marketplace_rooms.id) AS last_occupancy,
    (SELECT jsonb_build_object('start_at', start_at, 'end_at', end_at, 'reference', booking_reference)
     FROM marketplace_offers
     WHERE room_id = marketplace_rooms.id AND confirmed_at IS NOT NULL
       AND start_at <= now() AND end_at > now()
     ORDER BY start_at DESC LIMIT 1) AS current_booking,
    (SELECT jsonb_build_object('id', b.id, 'start_at', b.start_at, 'end_at', COALESCE(o.start_at, b.end_at))
     FROM marketplace_device_blocks b LEFT JOIN marketplace_openings o ON o.id = b.opening_id
     WHERE b.room_id = marketplace_rooms.id AND b.start_at <= now() AND COALESCE(o.start_at, b.end_at) > now()
     ORDER BY b.start_at DESC LIMIT 1) AS active_block
"""


class HostRoomOccupancy(BaseModel):
    occupied: bool
    changed_at: AwareDatetime


class HostRoomBooking(BaseModel):
    start_at: AwareDatetime
    end_at: AwareDatetime
    reference: str


class HostRoomBlock(BaseModel):
    id: UUID
    start_at: AwareDatetime
    end_at: AwareDatetime


class HostRoom(Room):
    published: bool
    last_occupancy: HostRoomOccupancy | None = None
    # Confirmed booking or scheduled block covering the current moment, if any.
    current_booking: HostRoomBooking | None = None
    active_block: HostRoomBlock | None = None


class HostRoomInput(BaseModel):
    name: ShortText
    city: ShortText
    venue: ShortText
    kind: RoomKind
    description: Description
    capacity: int = Field(ge=1, le=100)
    equipment: list[EquipmentName] = Field(default_factory=list, max_length=15)
    hourly_rate_ore: int = Field(ge=1, le=10_000_000)

    @field_validator("equipment")
    @classmethod
    def normalize_equipment(cls, equipment: list[str]) -> list[str]:
        return db._equipment(equipment)


class HostRoomPatch(BaseModel):
    details: HostRoomInput | None = None
    published: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "HostRoomPatch":
        if self.details is None and self.published is None:
            raise ValueError("Supply listing details or a publication status")
        return self


class HostReleaseInput(BaseModel):
    duration_minutes: int = Field(ge=15, le=720)
    release_id: UUID | None = None


class HostBlockInput(BaseModel):
    starts_at: AwareDatetime
    ends_at: AwareDatetime


class HostBlock(BaseModel):
    id: UUID
    start_at: AwareDatetime
    end_at: AwareDatetime


def require_host(user: Annotated[Account, Depends(require_user)]) -> Account:
    if user.role != "host":
        raise HTTPException(status_code=403, detail="A host account is required")
    return user


HostAccount = Annotated[Account, Depends(require_host)]


def _owned_room(connection, room_id: str, owner_id: UUID, *, lock: bool = False) -> dict:
    query = f"SELECT {_COLUMNS}, {_LIVE_STATUS} FROM marketplace_rooms WHERE id = %s AND owner_id = %s"
    if lock:
        query += " FOR UPDATE"
    room = connection.execute(query, (room_id, owner_id)).fetchone()
    if room is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return room


def _details(room: HostRoomInput) -> tuple:
    rate = room.hourly_rate_ore
    return (
        room.name, room.city, room.venue, room.kind, room.description,
        room.capacity, room.equipment, rate, max(1, rate * 7 // 10), rate * 3 // 2,
    )


@router.get("/rooms", response_model=list[HostRoom])
def list_host_rooms(host: HostAccount, response: Response) -> list[dict]:
    response.headers["Cache-Control"] = "no-store"
    with db._connect() as connection:
        return connection.execute(
            f"SELECT {_COLUMNS}, {_LIVE_STATUS} FROM marketplace_rooms WHERE owner_id = %s ORDER BY name, id",
            (host.id,),
        ).fetchall()


@router.post(
    "/rooms", status_code=201, response_model=HostRoom, dependencies=[Depends(require_browser_mutation)]
)
def create_host_room(body: HostRoomInput, host: HostAccount) -> dict:
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")[:48].rstrip("-") or "room"
    room_id = f"{slug}-{uuid4().hex[:12]}"
    with db._connect() as connection:
        return connection.execute(
            f"""
            INSERT INTO marketplace_rooms (
                id, owner_id, published, name, city, venue_name, kind, description, image_key,
                capacity, equipment, hourly_rate_ore, minimum_hourly_rate_ore, maximum_hourly_rate_ore
            )
            VALUES (%s, %s, false, %s, %s, %s, %s, %s, 'none', %s, %s, %s, %s, %s)
            RETURNING {_COLUMNS}
            """,
            (room_id, host.id, *_details(body)),
        ).fetchone()


@router.patch("/rooms/{room_id}", response_model=HostRoom, dependencies=[Depends(require_browser_mutation)])
def update_host_room(room_id: str, body: HostRoomPatch, host: HostAccount) -> dict:
    with db._connect() as connection:
        previous = _owned_room(connection, room_id, host.id, lock=True)
        capacity_or_equipment_changed = False
        if body.details is not None:
            details = body.details
            capacity_or_equipment_changed = (
                details.capacity != previous["capacity"] or details.equipment != previous["equipment"]
            )
            connection.execute(
                """
                UPDATE marketplace_rooms
                SET name = %s, city = %s, venue_name = %s, kind = %s, description = %s,
                    capacity = %s, equipment = %s, hourly_rate_ore = %s,
                    minimum_hourly_rate_ore = %s, maximum_hourly_rate_ore = %s
                WHERE id = %s AND owner_id = %s
                """,
                (*_details(details), room_id, host.id),
            )
        if body.published is not None:
            connection.execute(
                "UPDATE marketplace_rooms SET published = %s WHERE id = %s AND owner_id = %s",
                (body.published, room_id, host.id),
            )
        if body.published is False or capacity_or_equipment_changed:
            connection.execute(
                """
                UPDATE marketplace_offers SET expires_at = LEAST(expires_at, now())
                WHERE room_id = %s AND confirmed_at IS NULL AND expires_at > now()
                """,
                (room_id,),
            )
        return _owned_room(connection, room_id, host.id)


@router.post(
    "/rooms/{room_id}/blocks", status_code=201, response_model=HostBlock,
    dependencies=[Depends(require_browser_mutation)],
)
def schedule_host_block(room_id: str, body: HostBlockInput, host: HostAccount) -> dict:
    try:
        return db.schedule_device_block(room_id, body.starts_at, body.ends_at, owner_id=host.id)
    except db.NotFound as exc:
        raise HTTPException(status_code=404, detail="Listing not found") from exc
    except db.Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/rooms/{room_id}/release", response_model=ReleaseResult, dependencies=[Depends(require_browser_mutation)]
)
def release_host_room(
    room_id: str, body: HostReleaseInput, host: HostAccount, background_tasks: BackgroundTasks
) -> dict:
    from .main import ingest_release

    with db._connect() as connection:
        room = _owned_room(connection, room_id, host.id)
    if not room["published"]:
        raise HTTPException(status_code=409, detail="Publish this listing before releasing time")

    now = datetime.now(UTC)
    event_id = str(
        uuid5(NAMESPACE_URL, f"standbyroom:host-release:{host.id}:{room_id}:{body.release_id}")
        if body.release_id is not None else uuid4()
    )
    result = ingest_release({
        "source": "host",
        "event_id": event_id,
        "block_id": event_id,
        "external_room_id": room_id,
        "released_at": now,
        "scheduled_end_at": now + timedelta(minutes=body.duration_minutes),
    }, background_tasks)
    if result.get("reason") == "room_unpublished":
        raise HTTPException(status_code=409, detail="Publish this listing before releasing time")
    return result


class LiveSpan(BaseModel):
    start_at: AwareDatetime
    end_at: AwareDatetime


class LiveRoom(BaseModel):
    """Occupancy and booked/free for a demo room. No references, owners or renters."""
    id: str
    name: str
    venue: str
    last_occupancy: HostRoomOccupancy | None = None
    current_booking: LiveSpan | None = None
    active_block: LiveSpan | None = None


@public_router.get("/rooms/{room_id}/live", response_model=LiveRoom)
def live_room(room_id: str, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    if room_id not in LIVE_ROOM_IDS:
        raise HTTPException(status_code=404, detail="Room not found")
    with db._connect() as connection:
        room = connection.execute(
            f"SELECT id, name, venue_name AS venue, {_LIVE_STATUS} FROM marketplace_rooms WHERE id = %s",
            (room_id,),
        ).fetchone()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room
