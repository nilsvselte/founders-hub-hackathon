"""Prepare a local Google Calendar update after an approved booking."""

from collections.abc import Mapping
from datetime import UTC, datetime
from html import escape
from urllib.parse import urlsplit

from .rules import event_interval


def build_write_back(
    event: Mapping[str, object],
    *,
    booked_start: datetime,
    booked_end: datetime,
    room_name: str,
    venue_address: str,
    booking_reference: str,
    booking_url: str,
) -> dict | None:
    """Plan an update to a freshly fetched event. The caller owns consent and delivery."""
    organizer = event.get("organizer")
    if not isinstance(organizer, Mapping) or organizer.get("self") is not True:
        raise ValueError("Only the organizer can add a room to the shared event")
    if event.get("status") == "cancelled" or event.get("recurrence") or event.get("attendeesOmitted") is True:
        raise ValueError("Fetch a complete, active event instance before updating it")
    if booked_start.utcoffset() is None or booked_end.utcoffset() is None:
        raise ValueError("The booking time must include a time zone")
    if event_interval(event) != (booked_start.astimezone(UTC), booked_end.astimezone(UTC)):
        raise ValueError("The meeting time no longer matches the booked slot")

    room_name, venue_address, booking_reference = (value.strip() for value in (room_name, venue_address, booking_reference))
    if any(not value or len(value.splitlines()) != 1 for value in (room_name, venue_address, booking_reference)):
        raise ValueError("The confirmed room, venue address, and booking reference are required")
    url = urlsplit(booking_url)
    if url.scheme not in {"http", "https"} or not url.hostname or url.username is not None or any(
        char.isspace() for char in booking_url
    ):
        raise ValueError("The booking URL must be an HTTP or HTTPS URL")

    location = f"{room_name}, {venue_address}"
    current_location = event.get("location", "")
    if current_location and current_location != location:
        raise ValueError("The meeting already has a different location")
    description = event.get("description") or ""
    if not isinstance(description, str):
        raise ValueError("The meeting description must be text")
    booking_line = f"Booked via standbyroom: {escape(booking_reference)} {escape(booking_url)}"
    existing_lines = [line for line in description.splitlines() if line.startswith("Booked via standbyroom: ")]
    if any(line != booking_line for line in existing_lines):
        raise ValueError("The meeting already has a different standbyroom booking")
    if existing_lines and current_location == location:
        return None
    if not existing_lines:
        description = f"{description}\n\n{booking_line}" if description else booking_line
    return {"body": {**event, "location": location, "description": description}, "sendUpdates": "none"}
