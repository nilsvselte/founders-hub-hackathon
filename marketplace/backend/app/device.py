"""Translate device data into marketplace releases.

Set MARKETPLACE_DEVICE_ADAPTER to ``module:factory`` to load another adapter.
The factory takes no arguments and returns an object implementing DeviceAdapter.
A webhook or polling integration can pass its data through this same boundary.
The marketplace owns room mapping, event deduplication, and availability.
"""

import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from importlib import import_module
from typing import Protocol, TypedDict
from uuid import uuid4


class InvalidDevicePayload(ValueError):
    """An event could not be parsed as device data."""


class RoomRelease(TypedDict):
    source: str
    event_id: str
    external_room_id: str
    block_id: str
    released_at: datetime
    scheduled_end_at: datetime


class DeviceAdapter(Protocol):
    def normalize_release(self, payload: Mapping[str, object]) -> RoomRelease | None:
        """Return an explicit release with stable IDs, or None for unrelated data."""
        ...


def _required_id(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise InvalidDevicePayload(f"{key} must be a nonempty string up to 128 characters")
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
    """Decode the demo format while the physical device API is being defined."""

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
def _load_adapter(spec: str) -> DeviceAdapter:
    if spec == "fixture":
        return FixtureDeviceAdapter()

    module_name, separator, factory_name = spec.partition(":")
    if not separator or not module_name or not factory_name:
        raise RuntimeError("MARKETPLACE_DEVICE_ADAPTER must be 'fixture' or 'module:factory'")

    try:
        factory = getattr(import_module(module_name), factory_name)
        adapter = factory()
    except (ImportError, AttributeError, TypeError) as exc:
        raise RuntimeError("Could not load the configured device adapter") from exc

    if not callable(getattr(adapter, "normalize_release", None)):
        raise RuntimeError("The configured device adapter must provide normalize_release()")
    return adapter


def load_device_adapter() -> DeviceAdapter:
    return _load_adapter(os.getenv("MARKETPLACE_DEVICE_ADAPTER", "fixture").strip())
