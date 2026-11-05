---
name: room-matching
description: Finding, ranking, and explaining room suggestions for a calendar meeting. Use when building POST /suggestions, choosing the top 3 rooms, changing ranking signals, or writing the reason shown to the user.
---

# Room matching

## What exists (backend, `marketplace/backend/app/`)

- `db.list_candidates(request_id)`: filters released openings for a standby request by published, capacity ≥ party, equipment, time window, busy gaps, price ≤ `max_price_ore`, and room/venue.
- `matching.select_match(request, candidates)`: picks one. With an API key it calls Claude Haiku (paid: keep `MARKETPLACE_DEMO_MODE=1` and no key); demo mode picks the cheapest.
- `pricing.quote_price()`: Oslo time bands (weekend −20%, weekday 09–16 +20%, else −15%, −10% if starting within 30 min), clamped to the room's min/max.
- `GET /rooms`, `GET /rooms/{id}`, `GET /rooms/{room_id}/quote?start_at=&duration_minutes=`.
- `venues.py`: 29 venues with addresses, no coordinates.
- Only **released** openings (`marketplace_openings`) are bookable. For the demo, seed openings or call `POST /demo/release`.

## Tonight (no backend change)

1. `GET /rooms`; drop rooms that fail the hard filters below.
2. `GET /rooms/{id}/quote` for the meeting's start and length on each remaining room.
3. Rank with the signals below in the agent (Claude, on the subscription) and show the top 3.

## Planned: `POST /suggestions`

Input: the meeting (start, end, party size, equipment, rough area) plus the caller's preferences. Output: the top 3 candidates, each with room, venue, address, start/end, quote, and a reason. Creates nothing: no request, no offer, no hold. Reuse the `list_candidates` filter logic rather than a second copy. Ranking is deterministic in the backend; Claude only phrases the reason.

## Ranking signals, in order

Hard filters (fail one → out):
1. Capacity ≥ attendees.
2. Free for the whole time window and duration.
3. Price ≤ ceiling (`max_price_ore`).
4. Required equipment present; venue not in `avoid_venues`.

Soft signals (sort by):
1. Close to where attendees are, or to where the user is before and after (straight-line walking time from venue lat/lon once added; Entur later).
2. Preferred or recently used venue.
3. Room kind matches (quiet, boardroom, social).
4. Cheaper, including off-peak quotes.

## Explanation format

One line per suggestion, naming the signals that won:

```
Mesh Youngstorget, Room 3 · 14:00–15:00 · 320 kr
For 4 people with a screen, 6 min walk from your 13:00, under your 400 kr/h ceiling.
```

- Price from the quote, in kroner. Mention the quote's own reason when it is a discount ("off-peak −15%").
- Refer to the meeting by time, not by title, when the text leaves the user's side.
- If nothing passes the hard filters, say which filter emptied the list and offer to relax it.

Done when the user sees 1–3 suggestions, each with price and reason, or a clear "no room" with the blocking filter. Booking is `booking`.
