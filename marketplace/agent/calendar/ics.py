"""Preview candidate meeting slots from a local calendar export."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .rules import OSLO, SCAN_WINDOW, SuggestionInput, scan_events


MAX_EXPORT_BYTES = 4 * 1024 * 1024


def _time(value: object) -> dict[str, str]:
    if not isinstance(value, datetime):
        return {}
    return {"dateTime": value.isoformat(), "timeZone": OSLO.key}


def _address(value: object) -> str:
    return str(value).removeprefix("mailto:") if value is not None else ""


def _as_event(event) -> dict:
    attendees = event.get("ATTENDEE", [])
    if not isinstance(attendees, list):
        attendees = [attendees]
    organizer = _address(event.get("ORGANIZER"))
    return {
        "start": _time(event.decoded("DTSTART", None)),
        "end": _time(event.decoded("DTEND", None)),
        "status": str(event.get("STATUS", "")).lower(),
        "transparency": str(event.get("TRANSP", "")).lower(),
        "location": str(event.get("LOCATION", "")),
        "description": str(event.get("DESCRIPTION", "")),
        "summary": str(event.get("SUMMARY", "")),
        "conferenceData": event.get("CONFERENCE") or event.get("X-GOOGLE-CONFERENCE"),
        "organizer": {"email": organizer} if organizer else {},
        "attendees": [
            {
                "email": _address(attendee),
                "resource": str(attendee.params.get("CUTYPE", "")).upper() in {"RESOURCE", "ROOM"},
                "responseStatus": str(attendee.params.get("PARTSTAT", "")).lower(),
            }
            for attendee in attendees
        ],
    }


def scan_ics(data: bytes, *, now: datetime | None = None, rough_area: str | None = None) -> list[SuggestionInput]:
    import recurring_ical_events
    from icalendar import Calendar

    if len(data) > MAX_EXPORT_BYTES:
        raise ValueError("The calendar export exceeds 4 MiB")
    now = datetime.now(UTC) if now is None else now
    if now.utcoffset() is None:
        raise ValueError("The scan time must include a time zone")
    now = now.astimezone(UTC)
    calendar = Calendar.from_ical(data)
    events = recurring_ical_events.of(calendar).between(now.astimezone(OSLO), (now + SCAN_WINDOW).astimezone(OSLO))
    return scan_events((_as_event(event) for event in events), now=now, rough_area=rough_area)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="Path to a local .ics file")
    parser.add_argument("--rough-area", help="Public area to search, such as Trondheim")
    args = parser.parse_args()
    try:
        with args.export.open("rb") as export:
            data = export.read(MAX_EXPORT_BYTES + 1)
        result = scan_ics(data, rough_area=args.rough_area)
    except ModuleNotFoundError:
        parser.exit(2, "Install icalendar and recurring-ical-events to scan an ICS export.\n")
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        parser.exit(2, "Could not read the local calendar export.\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
