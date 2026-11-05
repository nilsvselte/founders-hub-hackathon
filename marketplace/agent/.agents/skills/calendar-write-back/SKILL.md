---
name: calendar-write-back
description: Writing a booked room back into the user's Google Calendar event (location and description). Use after a booking succeeds, or when changing what the agent writes to events.
---

# Calendar write-back

Status: **planned** (`marketplace/agent/calendar/google.py`). Needs the OAuth path from `calendar-scan`; the ICS link is read-only. The frontend already offers an "add to Google Calendar" link for confirmed bookings; that creates a new event, while this skill updates the existing meeting.

## What to write

- `location`: `"{room name}, {venue address}"`.
- `description`: the existing text, then a blank line and `Booked via standbyroom: {booking ref} {booking url}`.

Nothing else changes: attendees, times, title, and reminders stay as they are. Room resources as attendees only work with Workspace room calendars; leave them out.

## Steps

1. Get the event fresh: `events().get(calendarId="primary", eventId=eid)`. Use get → update, not patch: patch replaces whole arrays.
2. Set `location`; append to `description`.
3. Update with `sendUpdates="none"` so no invite goes to attendees.

```python
creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/calendar.events"])
svc = build("calendar", "v3", credentials=creds)
ev = svc.events().get(calendarId="primary", eventId=eid).execute()
ev["location"] = f"{room.name}, {room.address}"
ev["description"] = (ev.get("description") or "") + f"\n\nBooked via standbyroom: {ref} {url}"
svc.events().update(calendarId="primary", eventId=eid, body=ev, sendUpdates="none").execute()
```

In assistant mode, Claude does the same through the connector's update-event tool, with the same two fields and no notifications.

## `organizer.self` caveat

If the user is not the organizer, the update changes only their own copy; other attendees still see no room. Tell the user and offer the text to send to the organizer instead. No-scope alternative: the marketplace sends its own `.ics` invite.

Done when the event shows the room address and ref, and no attendee got an update.
