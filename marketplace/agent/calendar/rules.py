"""Classify calendar events locally and build privacy-limited suggestion inputs."""

import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from typing import NotRequired, TypedDict
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


OSLO = ZoneInfo("Europe/Oslo")
SCAN_WINDOW = timedelta(days=7)
VIDEO_HOSTS = (
    "meet.google.com", "teams.microsoft.com", "teams.live.com", "teams.cloud.microsoft",
    "zoom.us", "zoom.com", "zoomgov.com",
)
VIDEO_LINK = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)


class SuggestionInput(TypedDict):
    start_at: str
    end_at: str
    party_size: int
    rough_area: NotRequired[str]


def _instant(value: object) -> datetime | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("dateTime"), str):
        return None
    raw_time = value["dateTime"]
    if "T" not in raw_time:
        return None
    try:
        timestamp = datetime.fromisoformat(raw_time)
        if timestamp.tzinfo is None:
            zone_name = value.get("timeZone")
            if not isinstance(zone_name, str):
                return None
            zone = ZoneInfo(zone_name)
            local = timestamp.replace(tzinfo=zone)
            # An offset-free clock time near a transition might denote zero or two instants.
            if local.utcoffset() != local.replace(fold=1).utcoffset():
                return None
            timestamp = local
        return timestamp.astimezone(UTC)
    except (ValueError, OverflowError, ZoneInfoNotFoundError):
        return None


def event_interval(event: Mapping[str, object]) -> tuple[datetime, datetime] | None:
    start, end = _instant(event.get("start")), _instant(event.get("end"))
    if start is None or end is None or end <= start:
        return None
    return start, end


def _web_host(text: str) -> str:
    if text.startswith("www."):
        text = f"https://{text}"
    try:
        url = urlsplit(text)
        if url.scheme in {"http", "https"} and not any(char.isspace() for char in text):
            return url.hostname or ""
    except ValueError:
        pass
    return ""


def _video_link(text: object) -> bool:
    if not isinstance(text, str):
        return False
    for link in VIDEO_LINK.findall(text):
        host = _web_host(link.lower().rstrip(".,;!?)]}"))
        if any(host == suffix or host.endswith(f".{suffix}") for suffix in VIDEO_HOSTS):
            return True
    return False


def _identity(attendee: Mapping[str, object]) -> str:
    email = attendee.get("email")
    return email.strip().casefold() if isinstance(email, str) else ""


def _headcount(event: Mapping[str, object]) -> int | None:
    attendees = event.get("attendees", [])
    if event.get("attendeesOmitted") is True or not isinstance(attendees, list):
        return None
    organizer = event.get("organizer")
    organizer_email = _identity(organizer) if isinstance(organizer, Mapping) else ""
    organizer_in_list = False
    people = 0
    seen: set[str] = set()

    for attendee in attendees:
        if not isinstance(attendee, Mapping) or attendee.get("resource") is True:
            return None
        declined = attendee.get("responseStatus") == "declined"
        if attendee.get("self") is True and declined:
            return None
        email = _identity(attendee)
        if attendee.get("organizer") is True or (organizer_email and organizer_email == email):
            organizer_in_list = True
        if not declined and (not email or email not in seen):
            people += 1
            if email:
                seen.add(email)
    if isinstance(organizer, Mapping) and organizer and not organizer_in_list:
        people += 1
    return people


def suggestion_input(
    event: Mapping[str, object], *, now: datetime | None = None, rough_area: str | None = None,
) -> SuggestionInput | None:
    """Use a caller-selected area only. Calendar text never leaves this function."""
    now = datetime.now(UTC) if now is None else now
    if now.utcoffset() is None:
        raise ValueError("The scan time must include a time zone")
    now = now.astimezone(UTC)
    if (
        event.get("status") == "cancelled"
        or event.get("eventType", "default") != "default"
        or event.get("transparency") == "transparent"
        or event.get("endTimeUnspecified") is True
    ):
        return None
    interval = event_interval(event)
    if interval is None:
        return None
    start, end = interval
    seconds = (end - start).total_seconds()
    if not now <= start < now + SCAN_WINDOW or not 900 <= seconds <= 43_200 or seconds % 60:
        return None
    people = _headcount(event)
    if people is None or not 2 <= people <= 100:
        return None
    location = event.get("location")
    if isinstance(location, str) and location.strip() and not _web_host(location.strip().lower()):
        return None
    if event.get("hangoutLink") or event.get("conferenceData") or any(
        _video_link(event.get(key)) for key in ("location", "description", "summary")
    ):
        return None

    result = SuggestionInput(
        start_at=start.astimezone(OSLO).isoformat(), end_at=end.astimezone(OSLO).isoformat(), party_size=people,
    )
    if rough_area and (area := " ".join(rough_area.split())):
        if len(area) > 80:
            raise ValueError("Use a public area name of 80 characters or fewer")
        result["rough_area"] = area
    return result


def needs_room(event: Mapping[str, object], *, now: datetime | None = None) -> bool:
    return suggestion_input(event, now=now) is not None


def scan_events(
    events: Iterable[Mapping[str, object]], *, now: datetime | None = None, rough_area: str | None = None,
) -> list[SuggestionInput]:
    now = datetime.now(UTC) if now is None else now
    suggestions = (suggestion_input(event, now=now, rough_area=rough_area) for event in events)
    return sorted(
        (item for item in suggestions if item is not None),
        key=lambda item: datetime.fromisoformat(item["start_at"]),
    )
