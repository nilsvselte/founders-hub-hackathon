# Calendar preview

From the repository root, scan the next seven days of a local `.ics` export. The command prints only the Oslo timestamps and headcount needed by the marketplace suggestion API. An optional rough area must be a public place name you choose.

```sh
uv run --python 3.12 --with icalendar==6.3.1 --with recurring-ical-events==3.8.0 \
  python -m marketplace.agent.calendar.ics /path/to/demo.ics --rough-area Trondheim
```

Recurring meetings are expanded within the scan window, including exceptions. The scanner ignores all-day events, declined meetings where the current user is known, events that already have a location or room resource, and online calls. An ICS export does not reliably identify the current attendee. See the [recurrence library documentation](https://recurring-ical-events.readthedocs.io/en/v3.8.0/reference/api.html).

For assistant mode, Claude reads the Google Calendar connector locally and sends the same `start_at`, `end_at`, `party_size`, and optional `rough_area` fields to `suggest_rooms`. Keep meeting titles, attendee names and emails, event IDs, and descriptions inside the calendar assistant.

`rules.scan_events` accepts Google Calendar event JSON. `google.build_write_back` builds an update for a freshly fetched event after booking. It requires the organizer and the same booked interval, preserves existing event fields, and sets `sendUpdates` to `none`. The helper does not connect to Google. A caller with consent must submit the update. See [Google Calendar Events](https://developers.google.com/workspace/calendar/api/v3/reference/events) and the [update method](https://developers.google.com/workspace/calendar/api/v3/reference/events/update).

```sh
uv run --python 3.12 --with icalendar==6.3.1 --with recurring-ical-events==3.8.0 \
  python -m unittest marketplace.agent.calendar.test_calendar -v
```
