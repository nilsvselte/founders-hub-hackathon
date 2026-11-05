---
name: preferences
description: Account preferences for the marketplace agent (price ceiling, room types, equipment, favourite and avoided venues, home area). Use when adding the preferences table or GET/PUT /me/preferences, or when filling a standby request or ranking from preferences.
---

# Preferences

Status: **planned**. Today an `Account` (`marketplace/backend/app/accounts.py`) has only id, name, email, role, and `GET /me` returns it. A standby request takes a free-text `preferences` field (max 1000 chars) and nothing is stored per user.

## Schema (proposed)

New table `marketplace_user_preferences`, one row per account, added as a migration in `marketplace/backend/app/migrations/`:

| Column | Type | Meaning |
| --- | --- | --- |
| `user_id` | uuid, PK, FK accounts | Owner |
| `max_hourly_ore` | int, null | Price ceiling per hour, in øre (NOK × 100) |
| `default_equipment` | text[] | Always wanted, e.g. `{screen, whiteboard}`; same names as `EquipmentName` |
| `room_kinds` | text[] | e.g. `{quiet, boardroom, social}` |
| `preferred_venues` | text[] | Venue ids ranked first |
| `avoid_venues` | text[] | Venue ids never suggested |
| `home_lat`, `home_lon` | float, null | Rough home/office point for travel time |
| `max_travel_min` | int, null | Longest acceptable walk |
| `notes` | text | Free text, max 1000 chars |
| `updated_at` | timestamptz | |

Store a rough point (a street or campus), not an exact address.

## API (proposed)

- `GET /me/preferences` → the row, or defaults if none exists.
- `PUT /me/preferences` → full replace, validated with a Pydantic model in `schemas.py` beside `StandbyRequestInput`. Requires `require_user` and the `x-marketplace-request: 1` header like other mutations.
- The MCP server exposes them read-only to the agent (`get_preferences`); only the user edits them, on the account page.

## Filling a standby request

`POST /standby-requests` takes `StandbyRequestInput`. Build it from the meeting plus preferences:

| Field | From |
| --- | --- |
| `earliest_start`, `latest_end` | The meeting's start and end (add slack only if the user allows it) |
| `duration_minutes` | Meeting length |
| `party_size` | Headcount from the calendar |
| `equipment` | `default_equipment` ∪ what the meeting needs |
| `max_price_ore` | `max_hourly_ore` × hours; when unset, ask the user. Always set it |
| `room_id` | The room the user approved |
| `preferences` | `room_kinds` + `notes` as short text, with no calendar text |

## Ranking

Hard filters: `avoid_venues`, `max_price_ore`, `default_equipment`. Soft signals: `preferred_venues`, `room_kinds`, travel time from `home_lat/lon`. Order and weights live in `room-matching`. Every suggestion's reason names the preference it used ("your favourite venue", "under your 400 kr/h ceiling").
