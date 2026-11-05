"""Local stdio tools for standbyroom. The marketplace owns booking decisions."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, timedelta
from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StringConstraints, TypeAdapter


RoomId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
PartySize = Annotated[int, Field(ge=1, le=100)]
Price = Annotated[int, Field(ge=1, le=10_000_000)]
EquipmentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Equipment = Annotated[list[EquipmentName], Field(max_length=15)]
ReadOnly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)
BookingAction = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)
AwareDatetimeAdapter = TypeAdapter(AwareDatetime)


class RoomApproval(BaseModel):
    """The specific room, time, and maximum total price the renter approved."""

    model_config = ConfigDict(extra="forbid")

    room_id: RoomId
    start_at: AwareDatetime
    end_at: AwareDatetime
    max_price_ore: Price

    def duration_minutes(self) -> int:
        seconds = (self.end_at.astimezone(UTC) - self.start_at.astimezone(UTC)).total_seconds()
        if not 60 <= seconds <= 720 * 60 or seconds % 60:
            raise ToolError("The approved booking must last 1–720 whole minutes.")
        return int(seconds // 60)


class ApprovalForm(BaseModel):
    approve: Annotated[bool, Field(description="Confirm this specific room, time, and maximum price.")]


class SlotTaken(ToolError):
    """The marketplace returned a conflict on acceptance."""


@dataclass
class Runtime:
    client: httpx.AsyncClient
    booking_lock: asyncio.Lock


def _origin() -> str:
    origin = os.getenv("MARKETPLACE_API_URL", "http://127.0.0.1:8001").strip().rstrip("/")
    parsed = urlsplit(origin)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not parsed.hostname or parsed.username is not None or parsed.password is not None
        or parsed.query or parsed.fragment or parsed.path not in {"", "/api"}
        or (parsed.scheme != "https" and not (parsed.scheme == "http" and local))
    ):
        raise ValueError("MARKETPLACE_API_URL must be an HTTPS origin or a local HTTP origin, optionally ending in /api.")
    return origin


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[Runtime]:
    token = os.getenv("MARKETPLACE_API_TOKEN", "").strip()
    if not token:
        raise ValueError("Set MARKETPLACE_API_TOKEN to the renter's agent token before starting.")
    async with httpx.AsyncClient(
        base_url=_origin(),
        headers={"Authorization": f"Bearer {token}", "X-Marketplace-Request": "1"},
        follow_redirects=False,
        timeout=12.0,
        trust_env=False,
    ) as client:
        yield Runtime(client=client, booking_lock=asyncio.Lock())


mcp = FastMCP(
    "standbyroom",
    lifespan=_lifespan,
    instructions=(
        "Use suggestions to find available rooms. Before calling hold_room or confirm_booking, "
        "get the renter's explicit yes to the exact room, time, and total price in NOK. "
        "A yes to finding options is not a yes to book. Only one meeting per approval. "
        "After a conflict, any different room, time, or higher price requires fresh approval. "
        "Send only times, headcount, equipment, a rough area and budget from calendars. "
        "Keep titles, attendee names, emails and descriptions in the calendar connector."
    ),
)


def _runtime(ctx: Context) -> Runtime:
    return ctx.request_context.lifespan_context


async def _call(runtime: Runtime, method: str, path: str, **kwargs: Any) -> Any:
    try:
        response = await runtime.client.request(method, path, **kwargs)
    except httpx.RequestError as exc:
        raise ToolError("The marketplace API could not be reached. Check the local service and try again.") from exc
    if response.status_code in {401, 403}:
        raise ToolError("Agent access was denied. Check the renter token in the local agent environment.")
    if response.status_code == 409:
        raise SlotTaken("That offer is no longer available.")
    if response.status_code == 404:
        raise ToolError("The marketplace could not find that room or request.")
    if response.status_code == 422:
        raise ToolError("The marketplace could not use those booking details. Check the time, headcount and budget.")
    if not response.is_success:
        raise ToolError(f"The marketplace request failed (HTTP {response.status_code}).")
    try:
        return response.json()
    except ValueError as exc:
        raise ToolError("The marketplace returned an invalid response.") from exc


@mcp.tool(annotations=ReadOnly)
async def search_rooms(
    ctx: Context, party_size: PartySize = 1, city: str | None = None, equipment: Equipment | None = None,
) -> dict[str, Any]:
    """Browse published listings. Use suggest_rooms to check released availability for a meeting."""
    wanted = {item.casefold() for item in equipment or []}
    rooms = await _call(_runtime(ctx), "GET", "/rooms")
    return {"rooms": [
        room for room in rooms
        if room["capacity"] >= party_size
        and (city is None or room["city"].casefold() == city.strip().casefold())
        and wanted.issubset(item.casefold() for item in room["equipment"])
    ]}


@mcp.tool(annotations=ReadOnly)
async def quote_room(
    ctx: Context,
    room_id: RoomId,
    start_at: AwareDatetime,
    duration_minutes: Annotated[int, Field(ge=1, le=720)],
) -> dict[str, Any]:
    """Get a price estimate in Norwegian øre. A quote alone does not verify availability."""
    return await _call(_runtime(ctx), "GET", f"/rooms/{room_id}/quote", params={
        "start_at": start_at.isoformat(),
        "duration_minutes": duration_minutes,
    })


@mcp.tool(annotations=ReadOnly)
async def get_preferences(ctx: Context) -> dict[str, Any]:
    """Read the renter's room preferences shared with the calendar assistant."""
    return await _call(_runtime(ctx), "GET", "/me/agent-context")


@mcp.tool(annotations=ReadOnly)
async def suggest_rooms(
    ctx: Context,
    start_at: AwareDatetime,
    end_at: AwareDatetime,
    party_size: PartySize,
    equipment: Equipment | None = None,
    rough_area: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None,
    max_price_ore: Price | None = None,
) -> dict[str, Any]:
    """Find up to three available rooms. Creates no request, hold, or booking."""
    data: dict[str, Any] = {
        "start_at": start_at.isoformat(), "end_at": end_at.isoformat(), "party_size": party_size,
    }
    data.update({
        key: value for key, value in {
            "equipment": equipment, "rough_area": rough_area, "max_price_ore": max_price_ore,
        }.items() if value is not None
    })
    return await _call(_runtime(ctx), "POST", "/suggestions", json=data)


async def _require_approval(ctx: Context, approval: RoomApproval, approved: bool, action: str) -> None:
    if not approved:
        raise ToolError("Ask the renter to approve this exact room, time, and price before continuing.")
    params = ctx.session.client_params
    capability = params.capabilities.elicitation if params else None
    if capability is not None and (capability.form is not None or capability.url is None):
        result = await ctx.elicit(
            f"{action} room {approval.room_id} from {approval.start_at.isoformat()} to "
            f"{approval.end_at.isoformat()} for at most NOK {approval.max_price_ore / 100:.2f}?",
            ApprovalForm,
        )
        if result.action != "accept" or not result.data.approve:
            raise ToolError("The renter did not approve this booking action.")


def _same_time(value: str, approved: AwareDatetime) -> bool:
    try:
        instant = AwareDatetimeAdapter.validate_python(value)
        return instant.astimezone(UTC) == approved.astimezone(UTC)
    except (ValueError, OverflowError):
        return False


def _matching_offer(status: dict[str, Any], approval: RoomApproval) -> dict[str, Any] | None:
    if status.get("auto_confirm") is not False:
        raise ToolError("This request does not use the assistant's separate hold and confirmation flow.")
    if (
        status["room_id"] != approval.room_id
        or status["max_price_ore"] != approval.max_price_ore
        or not _same_time(status["earliest_start"], approval.start_at)
        or not _same_time(status["latest_end"], approval.end_at)
    ):
        raise ToolError("The request differs from the approved room, time, or price. Ask the renter before proceeding.")
    offer = status["offer"]
    if offer and (
        offer["price_ore"] > approval.max_price_ore
        or not _same_time(offer["start_at"], approval.start_at)
        or not _same_time(offer["end_at"], approval.end_at)
    ):
        raise ToolError("The offer differs from the approved time or price. Ask the renter before proceeding.")
    return offer


async def _wait_for_offer(runtime: Runtime, request_id: UUID, previous: str | None = None) -> dict[str, Any]:
    for attempt in range(5):
        status = await _call(runtime, "GET", f"/standby-requests/{request_id}")
        if status["status"] in {"expired", "confirmed"}:
            return status
        if status["offer"] and status["offer"]["id"] != previous:
            return status
        if attempt < 4:
            await asyncio.sleep(0.4)
    return status


@mcp.tool(annotations=BookingAction)
async def hold_room(
    ctx: Context,
    approval: RoomApproval,
    party_size: PartySize,
    approved: StrictBool,
    equipment: Equipment | None = None,
) -> dict[str, Any]:
    """Create a hold only after the renter says yes to the exact room, time, and total price."""
    duration = approval.duration_minutes()
    await _require_approval(ctx, approval, approved, "Hold")
    runtime = _runtime(ctx)
    async with runtime.booking_lock:
        result = await _call(runtime, "POST", "/standby-requests", json={
            "room_id": approval.room_id,
            "auto_confirm": False,
            "earliest_start": approval.start_at.isoformat(),
            "latest_end": approval.end_at.isoformat(),
            "duration_minutes": duration,
            "party_size": party_size,
            "max_price_ore": approval.max_price_ore,
            "equipment": equipment or [],
        })
        status = await _wait_for_offer(runtime, UUID(result["id"]))
        _matching_offer(status, approval)
        return status


@mcp.tool(annotations=BookingAction)
async def confirm_booking(
    ctx: Context, request_id: UUID, approval: RoomApproval, approved: StrictBool,
) -> dict[str, Any]:
    """Confirm a matching hold after renter approval. Retries a lost hold once for the exact same option."""
    approval.duration_minutes()
    await _require_approval(ctx, approval, approved, "Book")
    runtime = _runtime(ctx)
    async with runtime.booking_lock:
        status = await _wait_for_offer(runtime, request_id)
        offer = _matching_offer(status, approval)
        if status["status"] == "confirmed":
            return status
        if not offer:
            raise ToolError("There is no matching hold to confirm. Refresh the suggestions before booking.")
        offer_id = UUID(offer["id"])
        try:
            return await _call(runtime, "POST", f"/standby-requests/{request_id}/offers/{offer_id}/accept")
        except SlotTaken:
            status = await _call(runtime, "POST", f"/standby-requests/{request_id}/retry")
            if status["status"] == "expired":
                raise ToolError("The approved time has expired. Ask the renter before choosing another option.") from None
            status = await _wait_for_offer(runtime, request_id, str(offer_id))
            offer = _matching_offer(status, approval)
            if status["status"] == "confirmed":
                return status
            if offer and offer["id"] != str(offer_id):
                replacement_id = UUID(offer["id"])
                try:
                    return await _call(
                        runtime, "POST", f"/standby-requests/{request_id}/offers/{replacement_id}/accept",
                    )
                except SlotTaken:
                    pass
            raise ToolError("That room is no longer available at the approved time and price. Ask before switching.")


@mcp.tool(annotations=ReadOnly)
async def list_bookings(ctx: Context) -> dict[str, Any]:
    """List this renter's confirmed bookings and references."""
    history = await _call(_runtime(ctx), "GET", "/standby-requests")
    return {"bookings": [
        {
            "request_id": item["id"],
            "room_id": item["room_id"],
            "booking_reference": item["booking_reference"],
            "offer": item["offer"],
        }
        for item in history if item["status"] == "confirmed"
    ]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
