---
name: preferences
description: A renter's saved About, room preferences and agent settings (price ceiling, room kinds, equipment, favourite and avoided venues, home area, when to suggest and notify). Use when reading GET /me/agent-context, changing GET/PUT /me/preferences or the marketplace_user_preferences table, or when filling a standby request or ranking rooms from preferences.
---

# Preferences

Status: **built**. Renters edit them at `/account/preferences` in the marketplace (linked from their name in the header and from My bookings). Code: `marketplace/backend/app/preferences.py`, schemas in `schemas.py` (`AboutYou`, `RoomPreferences`, `AgentSettings`), table in migration `015_user_preferences.sql`. Only the user edits them; the agent reads them.

## Endpoints

All need a signed-in **renter** session (cookie; hosts get 403). Mutations need the `x-marketplace-request: 1` header.

| Endpoint | What it does |
| --- | --- |
| `GET /me/preferences` | `{about, preferences, agent, updated_at}`. Defaults when nothing is saved (`updated_at: null`). |
| `PUT /me/preferences` | Full replace with `{about, preferences, agent}`; returns the saved object. |
| `GET /me/agent-context` | **What the agent reads.** Compact summary with no name, email, account id or team name. |
| `GET /catalog/options` | Public. Room kinds, equipment and catalog venues (`id`, `name`, `city`) from published listings, for pickers and for mapping venue ids to names. |

## Fields

**about**: `team_name` (≤100, never sent to the agent), `what_we_do` (≤300), `usual_party_size` (1–100 or null), `home_area` (text, e.g. "Solsiden, Trondheim"), `home_lat`/`home_lon` (both or neither), `meeting_types` (any of `client_meeting`, `workshop`, `interview`, `team_day`, `board_meeting`, `offsite`), `agent_notes` (≤1000).

**preferences**: `max_hourly_ore` (øre per hour, null = unset), `room_kinds` (labels from `/catalog/options`, e.g. "Meeting room"), `equipment` (lower case, e.g. `screen`, `video conferencing`), `preferred_venues` / `avoid_venues` (venue ids such as `kowork`; never both), `max_travel_minutes` (1–240), `wishes` (≤1000).

**agent**: `suggest_for_unroomed_meetings` (default true), `suggestion_lead_days` (1, 3 or 7; default 3), `min_attendees_to_suggest` (default 2), `skip_online_meetings` (default true), `allow_notifications` (default false), `notification_channels` (`in_app`, `email`; stored only, nothing is sent yet), `quiet_hours_start` / `quiet_hours_end` (`HH:MM`, Oslo time, both or neither).

## Agent context shape

```json
{
  "has_saved_preferences": true,
  "about": {"what_we_do": "…", "usual_party_size": 4, "meeting_types": ["client_meeting"],
            "home": {"area": "Solsiden, Trondheim", "lat": 63.43, "lon": 10.41}, "notes_for_agent": "…"},
  "hard_filters": {"max_hourly_price_ore": 45000, "must_have_equipment": ["screen"],
                   "avoid_venue_ids": ["olo"], "max_travel_minutes": 15},
  "soft_preferences": {"room_kinds": ["Meeting room"], "preferred_venue_ids": ["kowork"], "wishes": "…"},
  "suggestions": {"suggest_for_unroomed_meetings": true, "lead_days": 3, "min_attendees": 2, "skip_online_meetings": true},
  "notifications": {"allowed": false, "channels": [], "quiet_hours": null}
}
```

Coordinates are rounded to 2 decimals (about 1 km). Nulls mean "not set": ask the user rather than guess.

## When to suggest

Scan only if `suggest_for_unroomed_meetings` is true, and only meetings within `lead_days`, with at least `min_attendees`, and (if `skip_online_meetings`) without a video link. Notify only if `allowed`, on the listed channels, and outside `quiet_hours`.

## Filling a standby request

`POST /standby-requests` takes `StandbyRequestInput`. Leave out `equipment` or `max_price_ore` and the backend fills them from the saved preferences (`max_hourly_ore` × duration, rounded up); with no saved price it returns 422. An explicit `equipment: []` means "no equipment needed" and is kept.

| Field | From |
| --- | --- |
| `earliest_start`, `latest_end` | The meeting's start and end |
| `duration_minutes` | Meeting length |
| `party_size` | Headcount from the calendar, else `usual_party_size` |
| `equipment` | Omit to use `must_have_equipment`, or send it plus what the meeting needs |
| `max_price_ore` | Omit to use the saved ceiling; when none is saved, ask the user |
| `room_id` | The room the user approved |
| `preferences` | `room_kinds` + `wishes` as short text, with no calendar text |

## Ranking

Hard filters: `avoid_venue_ids`, `max_hourly_price_ore`, `must_have_equipment`. Soft signals: `preferred_venue_ids`, `room_kinds`, `wishes`, travel time from `home`. Order and weights live in `room-matching`. Every suggestion's reason names the preference it used ("your favourite venue", "under your 450 kr/h ceiling").
