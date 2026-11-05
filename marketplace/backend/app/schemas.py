from datetime import datetime, time, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator, model_validator

EquipmentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
RoomId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class Room(BaseModel):
    id: str
    name: str
    city: str
    venue: str
    kind: str
    description: str
    image_key: str
    capacity: int
    equipment: list[str]
    hourly_rate_ore: int


class StandbyRequestInput(BaseModel):
    room_id: RoomId | None = None
    earliest_start: AwareDatetime
    latest_end: AwareDatetime
    duration_minutes: int = Field(ge=1, le=720)
    party_size: int = Field(ge=1, le=100)
    # Leave equipment or max_price_ore out to use the renter's saved preferences.
    equipment: list[EquipmentName] | None = Field(default=None, max_length=15)
    max_price_ore: int | None = Field(default=None, ge=1, le=10_000_000)
    preferences: str = Field(default="", max_length=1000)

    @field_validator("equipment")
    @classmethod
    def normalize_equipment(cls, equipment: list[str] | None) -> list[str] | None:
        return None if equipment is None else list(dict.fromkeys(item.lower() for item in equipment))

    @model_validator(mode="after")
    def validate_window(self) -> "StandbyRequestInput":
        try:
            earliest = self.earliest_start.astimezone(timezone.utc)
            latest = self.latest_end.astimezone(timezone.utc)
        except OverflowError as exc:
            raise ValueError("The request window is outside the supported date range") from exc
        if latest <= datetime.now(timezone.utc):
            raise ValueError("The end of the request window must be in the future")
        if latest - earliest < timedelta(minutes=self.duration_minutes):
            raise ValueError("The request window must fit the requested duration")
        return self


class OfferStatus(BaseModel):
    id: UUID
    room_name: str
    room_photo: str | None = None
    room_venue: str | None = None
    room_city: str | None = None
    start_at: AwareDatetime
    end_at: AwareDatetime
    price_ore: int
    expires_at: AwareDatetime
    match_reason: str
    match_provider: Literal["claude", "demo"]


class StandbyRequestStatus(BaseModel):
    id: UUID
    room_id: str | None
    room_name: str | None
    status: Literal["waiting", "offered", "confirmed", "expired"]
    offer: OfferStatus | None = None
    booking_reference: str | None = None
    earliest_start: AwareDatetime
    latest_end: AwareDatetime
    duration_minutes: int
    party_size: int
    equipment: list[str]
    max_price_ore: int
    preferences: str


class ReleaseResult(BaseModel):
    created: bool
    opening_id: UUID | None = None
    reason: str | None = None


class DemoReleaseInput(BaseModel):
    room_id: RoomId | None = None


class VenueInfo(BaseModel):
    id: str
    operator: str
    name: str
    location: str


MeetingType = Literal["client_meeting", "workshop", "interview", "team_day", "board_meeting", "offsite"]
ShortLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
VenueId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class AboutYou(BaseModel):
    team_name: str = Field(default="", max_length=100)
    what_we_do: str = Field(default="", max_length=300)
    usual_party_size: int | None = Field(default=None, ge=1, le=100)
    home_area: str = Field(default="", max_length=100)
    home_lat: float | None = Field(default=None, ge=-90, le=90)
    home_lon: float | None = Field(default=None, ge=-180, le=180)
    meeting_types: list[MeetingType] = Field(default_factory=list, max_length=6)
    agent_notes: str = Field(default="", max_length=1000)

    @field_validator("team_name", "what_we_do", "home_area", "agent_notes")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("meeting_types")
    @classmethod
    def unique_types(cls, values: list[str]) -> list[str]:
        return _unique(values)

    @model_validator(mode="after")
    def pair_coordinates(self) -> "AboutYou":
        if (self.home_lat is None) != (self.home_lon is None):
            raise ValueError("Give both latitude and longitude, or neither")
        return self


class RoomPreferences(BaseModel):
    max_hourly_ore: int | None = Field(default=None, ge=1, le=10_000_000)
    room_kinds: list[ShortLabel] = Field(default_factory=list, max_length=10)
    equipment: list[EquipmentName] = Field(default_factory=list, max_length=15)
    preferred_venues: list[VenueId] = Field(default_factory=list, max_length=30)
    avoid_venues: list[VenueId] = Field(default_factory=list, max_length=30)
    max_travel_minutes: int | None = Field(default=None, ge=1, le=240)
    wishes: str = Field(default="", max_length=1000)

    @field_validator("room_kinds", "preferred_venues", "avoid_venues")
    @classmethod
    def unique_values(cls, values: list[str]) -> list[str]:
        return _unique(values)

    @field_validator("equipment")
    @classmethod
    def normalize_equipment(cls, equipment: list[str]) -> list[str]:
        return _unique([item.lower() for item in equipment])

    @field_validator("wishes")
    @classmethod
    def strip_wishes(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def separate_venues(self) -> "RoomPreferences":
        if set(self.preferred_venues) & set(self.avoid_venues):
            raise ValueError("A venue can't be both preferred and avoided")
        return self


NotificationChannel = Literal["in_app", "email"]


class AgentSettings(BaseModel):
    allow_notifications: bool = False
    # Stored only for now; the marketplace sends no notifications yet.
    notification_channels: list[NotificationChannel] = Field(default_factory=list, max_length=2)
    suggest_for_unroomed_meetings: bool = True
    suggestion_lead_days: Literal[1, 3, 7] = 3
    min_attendees_to_suggest: int = Field(default=2, ge=1, le=100)
    skip_online_meetings: bool = True
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None

    @field_validator("notification_channels")
    @classmethod
    def unique_channels(cls, values: list[str]) -> list[str]:
        return _unique(values)

    @model_validator(mode="after")
    def pair_quiet_hours(self) -> "AgentSettings":
        if (self.quiet_hours_start is None) != (self.quiet_hours_end is None):
            raise ValueError("Give both a start and an end for quiet hours, or neither")
        return self


class UserPreferences(BaseModel):
    about: AboutYou = Field(default_factory=AboutYou)
    preferences: RoomPreferences = Field(default_factory=RoomPreferences)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    updated_at: AwareDatetime | None = None


class UserPreferencesInput(BaseModel):
    about: AboutYou = Field(default_factory=AboutYou)
    preferences: RoomPreferences = Field(default_factory=RoomPreferences)
    agent: AgentSettings = Field(default_factory=AgentSettings)


class CatalogVenue(BaseModel):
    id: str
    name: str
    city: str


class CatalogOptions(BaseModel):
    room_kinds: list[str]
    equipment: list[str]
    venues: list[CatalogVenue]
