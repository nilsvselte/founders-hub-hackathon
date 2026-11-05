---
name: booking
description: Booking an approved room through the marketplace's standby-request, offer, and accept flow. Use when turning a user's yes into a booking, handling a 409 or an expired offer, or changing hold length or cancel.
---

# Booking

## Guardrail

Book only after the user has said yes to one specific suggestion: room, time, and price. A yes to "find me rooms" is not a yes to book. One approval books one meeting. No payments: the marketplace confirms a booking with a ref and no charge.

## What exists (`marketplace/backend/app/main.py`, `db.py`)

1. `POST /standby-requests` with `StandbyRequestInput`: `room_id?`, `earliest_start`, `latest_end`, `duration_minutes`, `party_size`, `equipment[]`, `max_price_ore`, `preferences`. Matching runs as a background task.
2. `GET /standby-requests/{id}` until it has an offer. `db.create_offer()` holds the slot until `min(now + 5 min, start_at)`.
3. `POST /standby-requests/{id}/offers/{offer_id}/accept`. `db.accept_offer()` rechecks under a row lock and returns a booking ref (`MESH-...`).
4. A **409** means the offer expired or the slot is gone. `POST /standby-requests/{id}/retry` rematches.

Auth today: a cookie session plus the `x-marketplace-request: 1` header on mutations (`require_user` in `accounts.py`). An agent needs the planned per-user token (see `marketplace-mcp`).

## Steps

1. Build the request from the approved suggestion: set `room_id` to the approved room and the window to the meeting's start and end, filled per `preferences`. Always set `max_price_ore`.
2. Create it, poll for the offer, and check the offer matches what the user approved (room, time, price ≤ the quoted price).
3. Accept within the hold.
4. On 409: retry once for the same room. If it is still gone, show the user the next suggestion and ask again; a new room needs a new yes.
5. Report the booking ref, then hand off to `calendar-write-back`.

## Gaps (planned)

- **Hold length**: 5 minutes is short for a human approving in chat. Options: a `hold_minutes` field on the request, or create no request until the user approves (the flow above, recommended).
- **Bookable time**: only released openings are bookable. Demo: seed openings or `POST /demo/release`. Later: regular availability blocks per room.
- **Bookings list and cancel**: no `GET /bookings` or `DELETE /bookings/{ref}` yet. Cancel, when added, needs its own user yes.

Done when the user has a booking ref for the room they approved, or a clear message that it was taken and what was offered next.
