from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator, model_validator

EquipmentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class StandbyRequestInput(BaseModel):
    earliest_start: AwareDatetime
    latest_end: AwareDatetime
    duration_minutes: int = Field(ge=1, le=720)
    party_size: int = Field(ge=1, le=100)
    equipment: list[EquipmentName] = Field(default_factory=list, max_length=15)
    max_price_ore: int = Field(ge=1, le=10_000_000)
    preferences: str = Field(default="", max_length=1000)

    @field_validator("equipment")
    @classmethod
    def normalize_equipment(cls, equipment: list[str]) -> list[str]:
        return list(dict.fromkeys(item.lower() for item in equipment))

    @model_validator(mode="after")
    def validate_window(self) -> "StandbyRequestInput":
        if self.latest_end <= datetime.now(timezone.utc):
            raise ValueError("The end of the request window must be in the future")
        if self.latest_end - self.earliest_start < timedelta(minutes=self.duration_minutes):
            raise ValueError("The request window must fit the requested duration")
        return self


class OfferStatus(BaseModel):
    id: UUID
    room_name: str
    start_at: AwareDatetime
    end_at: AwareDatetime
    price_ore: int
    expires_at: AwareDatetime
    match_reason: str
    match_provider: Literal["claude", "demo"]


class StandbyRequestStatus(BaseModel):
    id: UUID
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
