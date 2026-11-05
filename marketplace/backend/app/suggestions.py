from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from . import db
from .accounts import Account, require_agent_or_user
from .preferences import load_preferences
from .pricing import PriceQuote
from .schemas import EquipmentName, RoomPreferences
from .venues import VENUES


class SuggestionRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError:
                # A malformed agent request may include private calendar fields.
                return JSONResponse(
                    {"detail": "Enter valid meeting details"}, status_code=422, headers={"Cache-Control": "no-store"},
                )

        return handle


router = APIRouter(tags=["agent"], route_class=SuggestionRoute)

_MAX_BOOKING_PRICE_ORE = 10_000_000
_ONE_MINUTE = timedelta(minutes=1)


class SuggestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_at: AwareDatetime
    end_at: AwareDatetime
    party_size: int = Field(ge=2, le=100, strict=True)
    equipment: list[EquipmentName] = Field(default_factory=list, max_length=15)
    rough_area: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    max_price_ore: int | None = Field(default=None, ge=1, le=_MAX_BOOKING_PRICE_ORE, strict=True)

    @field_validator("equipment")
    @classmethod
    def validate_equipment(cls, values: list[str]) -> list[str]:
        for value in values:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError("Enter valid equipment names") from None
            if "\0" in value:
                raise ValueError("Enter valid equipment names")
        return values

    @model_validator(mode="after")
    def validate_slot(self) -> "SuggestionInput":
        try:
            start, end = self.start_at.astimezone(UTC), self.end_at.astimezone(UTC)
        except OverflowError as exc:
            raise ValueError("Meeting times are outside the supported date range") from exc
        duration, remainder = divmod(end - start, _ONE_MINUTE)
        if remainder or not 15 <= duration <= 720:
            raise ValueError("Meeting duration must be 15 to 720 whole minutes")
        if start <= datetime.now(UTC):
            raise ValueError("The meeting must start in the future")
        return self

    @property
    def duration_minutes(self) -> int:
        return (self.end_at.astimezone(UTC) - self.start_at.astimezone(UTC)) // _ONE_MINUTE


class RoomSuggestion(BaseModel):
    room_id: str
    room_name: str
    venue_id: str | None
    venue: str | None
    city: str
    address: str | None
    kind: str
    capacity: int
    equipment: list[str]
    start_at: AwareDatetime
    end_at: AwareDatetime
    price_ore: int
    quote: PriceQuote
    reason: str


class SuggestionResult(BaseModel):
    suggestions: list[RoomSuggestion]
    message: str | None = None


def _place_matches(area: str, candidate: dict) -> bool:
    if not area:
        return False
    places = (candidate["room_city"], candidate["room_venue"], candidate["venue_id"])
    return any(place and area == place.casefold() for place in places)


def _room_kind_matches(candidate: dict, preferences: RoomPreferences) -> bool:
    kind = candidate["room_kind"].casefold()
    return any(kind == label.casefold() for label in preferences.room_kinds)


def _rank(candidate: dict, area: str, preferences: RoomPreferences) -> tuple:
    return (
        not _place_matches(area, candidate),
        candidate["venue_id"] not in preferences.preferred_venues,
        not _room_kind_matches(candidate, preferences),
        candidate["price_ore"],
        candidate["room_id"],
    )


def _format_candidate(candidate: dict, body: SuggestionInput, area: str, preferences: RoomPreferences) -> dict:
    known_venue = VENUES.get(candidate["venue_id"])
    # Some venues have a public location label but no verified street number.
    address = known_venue.location if known_venue and any(char.isdigit() for char in known_venue.location) else None
    reasons = [f"Fits {body.party_size} guests."]
    if _place_matches(area, candidate):
        reasons.append("Matches your preferred area.")
    if candidate["venue_id"] in preferences.preferred_venues:
        reasons.append("At a preferred venue.")
    if _room_kind_matches(candidate, preferences):
        reasons.append("Matches your preferred room type.")
    reasons.append(candidate["quote"]["reason"])
    return {
        "room_id": candidate["room_id"],
        "room_name": candidate["room_name"],
        "venue_id": candidate["venue_id"],
        "venue": candidate["room_venue"],
        "city": candidate["room_city"],
        "address": address,
        "kind": candidate["room_kind"],
        "capacity": candidate["capacity"],
        "equipment": candidate["equipment"],
        "start_at": candidate["start_at"],
        "end_at": candidate["end_at"],
        "price_ore": candidate["price_ore"],
        "quote": candidate["quote"],
        "reason": " ".join(reasons),
    }


@router.post("/suggestions", response_model=SuggestionResult)
def suggest_rooms(
    body: SuggestionInput,
    response: Response,
    account: Annotated[Account, Depends(require_agent_or_user)],
) -> dict:
    if account.role != "renter":
        raise HTTPException(status_code=403, detail="A renter account is required")
    response.headers["Cache-Control"] = "no-store"
    saved = load_preferences(account.id)
    preferences = saved.preferences
    budget = body.max_price_ore or _MAX_BOOKING_PRICE_ORE
    if preferences.max_hourly_ore is not None:
        budget = min(budget, preferences.max_hourly_ore * body.duration_minutes // 60)
    candidates = db.list_meeting_candidates(
        start_at=body.start_at,
        end_at=body.end_at,
        duration_minutes=body.duration_minutes,
        party_size=body.party_size,
        equipment=db._equipment([*body.equipment, *preferences.equipment]),
        max_price_ore=budget,
        avoid_venues=preferences.avoid_venues,
    )
    area = (body.rough_area or saved.about.home_area).casefold()
    suggestions = [
        _format_candidate(candidate, body, area, preferences)
        for candidate in sorted(candidates, key=lambda candidate: _rank(candidate, area, preferences))[:3]
    ]
    if suggestions:
        return {"suggestions": suggestions}
    return {
        "suggestions": [],
        "message": "No released room fits this time, group size, equipment, venue preferences and budget.",
    }
