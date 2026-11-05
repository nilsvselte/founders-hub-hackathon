import importlib.util
import unittest
from datetime import UTC, datetime

from .google import build_write_back
from .ics import scan_ics
from .rules import scan_events, suggestion_input


NOW = datetime.fromisoformat("2027-03-26T00:00:00+00:00")
START = datetime.fromisoformat("2027-03-28T01:45:00+01:00")
END = datetime.fromisoformat("2027-03-28T03:15:00+02:00")


def meeting(**changes):
    return {
        "id": "private-id",
        "summary": "private title",
        "description": "private description",
        "start": {"dateTime": START.isoformat()},
        "end": {"dateTime": END.isoformat()},
        "organizer": {"email": "organizer@example.test", "self": True},
        "attendees": [{"email": "attendee@example.test"}],
        **changes,
    }


class CalendarRulesTest(unittest.TestCase):
    def test_suggestion_contains_only_slot_headcount_and_explicit_area(self):
        result = suggestion_input(meeting(location="https://example.test/private-place"), now=NOW, rough_area=" Trondheim ")
        self.assertEqual(result, {
            "start_at": START.isoformat(), "end_at": END.isoformat(), "party_size": 2, "rough_area": "Trondheim",
        })
        self.assertNotIn("rough_area", suggestion_input(meeting(location="https://example.test/private-place"), now=NOW))

    def test_non_bookable_events_do_not_suggest_a_room(self):
        for changes in (
            {"status": "cancelled"}, {"eventType": "focusTime"}, {"transparency": "transparent"},
            {"start": {"date": "2027-03-28"}}, {"start": {"dateTime": "2027-03-01T09:00:00Z"}},
            {"start": {"dateTime": "2027-03-28T02:15:00", "timeZone": "Europe/Oslo"}},
            {"end": {"dateTime": "2027-03-28T01:50:00+01:00"}}, {"attendees": []},
            {"attendeesOmitted": True}, {"attendees": [{"resource": True}]},
            {"attendees": [{"self": True, "responseStatus": "declined"}]},
            {"location": "Existing meeting room"}, {"conferenceData": {"entryPoints": [{}]}},
            {"description": '<a href="https://us02web.zoom.us/j/private">Join the call</a>'},
            {"location": "https://teams.cloud.microsoft/meet/private"},
        ):
            with self.subTest(changes=changes):
                self.assertIsNone(suggestion_input(meeting(**changes), now=NOW))

    def test_duplicate_attendees_and_organizer_are_counted_once(self):
        event = meeting(attendees=[
            {"email": "organizer@example.test", "self": True},
            {"email": "attendee@example.test"},
            {"email": "ATTENDEE@example.test"},
            {"email": "absent@example.test", "responseStatus": "declined"},
        ])
        self.assertEqual(suggestion_input(event, now=NOW)["party_size"], 2)

    def test_clock_change_is_sorted_by_instant(self):
        start_later = "2027-10-31T02:05:00+01:00"
        start_earlier = "2027-10-31T02:55:00+02:00"
        end = {"dateTime": "2027-10-31T03:00:00+01:00"}
        events = [meeting(start={"dateTime": start}, end=end) for start in (start_later, start_earlier)]
        self.assertEqual([row["start_at"] for row in scan_events(events, now=datetime(2027, 10, 30, tzinfo=UTC))], [
            start_earlier, start_later,
        ])


@unittest.skipUnless(
    importlib.util.find_spec("icalendar") and importlib.util.find_spec("recurring_ical_events"),
    "requires optional ICS dependencies",
)
class IcsCalendarTest(unittest.TestCase):
    def test_expands_occurrences_and_preserves_wall_time_across_dst(self):
        data = "\r\n".join((
            "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//standbyroom//synthetic//EN",
            "BEGIN:VEVENT", "UID:private-ics", "DTSTAMP:20270326T000000Z",
            "DTSTART;TZID=Europe/Oslo:20270327T110000", "DTEND;TZID=Europe/Oslo:20270327T120000",
            "RRULE:FREQ=DAILY;COUNT=3", "EXDATE;TZID=Europe/Oslo:20270328T110000",
            "SUMMARY:Private recurring meeting", "DESCRIPTION:Never send this",
            "ORGANIZER:mailto:organizer@example.test", "ATTENDEE:mailto:attendee@example.test",
            "END:VEVENT", "END:VCALENDAR", "",
        )).encode()
        self.assertEqual(scan_ics(data, now=NOW), [
            {"start_at": "2027-03-27T11:00:00+01:00", "end_at": "2027-03-27T12:00:00+01:00", "party_size": 2},
            {"start_at": "2027-03-29T11:00:00+02:00", "end_at": "2027-03-29T12:00:00+02:00", "party_size": 2},
        ])


class GoogleWriteBackTest(unittest.TestCase):
    def plan(self, event):
        return build_write_back(
            event, booked_start=START, booked_end=END, room_name="Driv", venue_address="Trondheim",
            booking_reference="STANDBY-TEST", booking_url="http://127.0.0.1:3001/bookings/test",
        )

    def test_plan_updates_only_two_fields_and_repeat_is_noop(self):
        original = meeting(reminders={"useDefault": True}, recurrence=None)
        plan = self.plan(original)
        self.assertEqual(plan["sendUpdates"], "none")
        self.assertEqual(plan["body"], {
            **original, "location": "Driv, Trondheim",
            "description": "private description\n\nBooked via standbyroom: STANDBY-TEST http://127.0.0.1:3001/bookings/test",
        })
        self.assertNotIn("location", original)
        self.assertIsNone(self.plan(plan["body"]))

    def test_refuses_non_organizer_series_or_changed_meeting(self):
        for changes in (
            {"organizer": {"self": False}}, {"organizer": {}}, {"recurrence": ["RRULE:FREQ=WEEKLY"]},
            {"start": {"dateTime": "2027-03-28T01:50:00+01:00"}}, {"location": "Different room"},
            {"attendeesOmitted": True},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.plan(meeting(**changes))
