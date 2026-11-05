"""Translate device data into marketplace events.

Set MARKETPLACE_DEVICE_ADAPTER to ``module:factory`` to load another adapter.
The factory takes no arguments and returns an adapter implementing
``normalize_event`` or the original ``normalize_release`` method.
A webhook or polling integration can pass its data through this same boundary.
The marketplace owns room mapping, event deduplication, and availability.
"""

import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from importlib import import_module
from typing import Literal, Protocol, TypedDict
from uuid import uuid4


class InvalidDevicePayload(ValueError):
    """An event could not be parsed as device data."""


class RoomEventIdentity(TypedDict):
    source: str
    event_id: str
    external_room_id: str


class RoomRelease(RoomEventIdentity):
    block_id: str
    released_at: datetime
    scheduled_end_at: datetime


class RoomOccupancy(RoomEventIdentity):
    type: Literal["room.occupancy_changed"]
    occupied: bool
    changed_at: datetime


class RoomReleaseRequest(RoomEventIdentity):
    type: Literal["room.release_requested"]
    requested_at: datetime


DeviceEvent = RoomRelease | RoomOccupancy | RoomReleaseRequest


class DeviceAdapter(Protocol):
    def normalize_release(self, payload: Mapping[str, object]) -> RoomRelease | None:
        """Return an explicit release with stable IDs, or None for unrelated data."""
        ...


class EventDeviceAdapter(Protocol):
    def normalize_event(self, payload: Mapping[str, object]) -> DeviceEvent | None:
        """Return a supported event with stable IDs, or None for unrelated data."""
        ...


def _required_id(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise InvalidDevicePayload(f"{key} must be a nonempty string up to 128 characters")
    if "\0" in value:
        raise InvalidDevicePayload(f"{key} cannot contain a null character")
    try:
        value.encode()
    except UnicodeEncodeError as exc:
        raise InvalidDevicePayload(f"{key} must be valid UTF-8") from exc
    return value.strip()


def _timestamp(payload: Mapping[str, object], key: str) -> datetime:
    value = payload.get(key)
    if isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value)
            if timestamp.utcoffset() is not None:
                return timestamp.astimezone(UTC)
        except (ValueError, OverflowError):
            pass
    raise InvalidDevicePayload(f"{key} must be an ISO 8601 timestamp with a timezone")


class FixtureDeviceAdapter:
    """Decode the legacy format, which includes the scheduled block end."""

    def normalize_release(self, payload: Mapping[str, object]) -> RoomRelease | None:
        if _required_id(payload, "type") != "room.released":
            return None

        released_at = _timestamp(payload, "released_at")
        scheduled_end_at = _timestamp(payload, "scheduled_end_at")
        if scheduled_end_at <= released_at:
            raise InvalidDevicePayload("scheduled_end_at must be later than released_at")

        return RoomRelease(
            source="fixture",
            event_id=_required_id(payload, "event_id"),
            external_room_id=_required_id(payload, "external_room_id"),
            block_id=_required_id(payload, "block_id"),
            released_at=released_at,
            scheduled_end_at=scheduled_end_at,
        )


class AtechDeviceAdapter(FixtureDeviceAdapter):
    """Decode occupancy and button events from the Atech device server."""

    def normalize_event(self, payload: Mapping[str, object]) -> DeviceEvent | None:
        event_type = _required_id(payload, "type")
        if event_type not in {"room.occupancy_changed", "room.release_requested"}:
            return self.normalize_release(payload)

        identity = RoomEventIdentity(
            source="atech",
            event_id=_required_id(payload, "event_id"),
            external_room_id=_required_id(payload, "external_room_id"),
        )
        if event_type == "room.release_requested":
            return RoomReleaseRequest(
                type=event_type, requested_at=_timestamp(payload, "requested_at"), **identity,
            )

        occupied = payload.get("occupied")
        if not isinstance(occupied, bool):
            raise InvalidDevicePayload("occupied must be a boolean")
        return RoomOccupancy(
            type="room.occupancy_changed", occupied=occupied,
            changed_at=_timestamp(payload, "changed_at"), **identity,
        )


def demo_release_payload(room_id: str) -> dict[str, str]:
    now = datetime.now(UTC)
    return {
        "type": "room.released",
        "event_id": str(uuid4()),
        "external_room_id": room_id,
        "block_id": str(uuid4()),
        "released_at": now.isoformat(),
        "scheduled_end_at": (now + timedelta(hours=2)).isoformat(),
    }


@lru_cache(maxsize=1)
def _load_adapter(spec: str) -> DeviceAdapter | EventDeviceAdapter:
    if spec in {"atech", "fixture"}:
        return AtechDeviceAdapter()

    module_name, separator, factory_name = spec.partition(":")
    if not separator or not module_name or not factory_name:
        raise RuntimeError("MARKETPLACE_DEVICE_ADAPTER must be 'atech', 'fixture', or 'module:factory'")

    try:
        factory = getattr(import_module(module_name), factory_name)
        adapter = factory()
    except (ImportError, AttributeError, TypeError) as exc:
        raise RuntimeError("Could not load the configured device adapter") from exc

    if not any(callable(getattr(adapter, method, None)) for method in ("normalize_event", "normalize_release")):
        raise RuntimeError("The configured device adapter must provide normalize_event() or normalize_release()")
    return adapter


def load_device_adapter() -> DeviceAdapter | EventDeviceAdapter:
    return _load_adapter(os.getenv("MARKETPLACE_DEVICE_ADAPTER", "atech").strip())


def normalize_device_event(payload: Mapping[str, object]) -> DeviceEvent | None:
    adapter = load_device_adapter()
    normalize_event = getattr(adapter, "normalize_event", None)
    if callable(normalize_event):
        return normalize_event(payload)
    return adapter.normalize_release(payload)
