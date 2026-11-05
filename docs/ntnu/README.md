# NTNU student rooms

The marketplace's `/ntnu` page is an experimental student feature in standbyroom's
existing visual style. Students describe a group-room request, review matching
rooms, confirm one reservation, and see or cancel their NTNU bookings.

The public landing page and marketplace navigation both link to the feature.

## Current behavior

- **Try the demo** uses the existing [TP MCP](../../experiments/tp-room-booking-mcp/README.md)
  over its actual stdio protocol. A disclosed guided parser collects the request.
  Sample reservations persist between MCP calls and belong to one browser session.
  No real NTNU room is booked, and no developer TP session is used.
- **NTNU rooms** stays unavailable until an approved student integration is
  configured. It never substitutes sample rooms for a live search. In live mode,
  the configured Claude model extracts requirements; the backend calls the MCP
  for availability and creates a reservation only after the student's confirmation.
- Missing date, start time, duration, group size or campus produces a follow-up
  question. Campus and building names resolve against the connected MCP's location
  list. Only directly bookable group rooms are shown.
- Suggestions expire after ten minutes and belong to the authenticated student or
  demo browser. A confirmed suggestion returns its existing result if resubmitted.
  An uncertain submission cannot be automatically repeated.

The [routes](../../marketplace/backend/app/ntnu.py) keep demo and live access
separate. The [connection boundary](../../marketplace/backend/app/ntnu_access.py)
uses the marketplace account's server-authenticated ID, never a student ID supplied
by the browser. The website does not read `TP_STATE_FILE` or ask for TP cookies.

## Live integration boundary

`NTNU_INTEGRATION_FACTORY` names a trusted server factory (`module:create_integration`).
It must provide the `StudentIntegration` interface:

- `status(user_id)` returns `Connection(connected, connectable, label)`.
- `authorize(user_id, return_path)` starts an institution-approved authorization
  flow and returns its HTTPS authorization URL. Its origin must appear in
  `NTNU_AUTH_ALLOWED_ORIGINS`. The integration owns callback validation, credential
  storage, account linking and expiry.
- `session(user_id)` is an async context manager yielding an initialized MCP
  `ClientSession` authorized specifically for that student. Its tool envelopes must
  identify `backend: "tp"`. Sample envelopes are rejected in live mode.

The user ID passed to this adapter is the marketplace account ID. The adapter must
link it to the student's verified NTNU identity; it is not itself a TP username.
Ordinary Feide website sign-in does not establish TP API booking access.

### Pending: institution-approved TP access

> TODO: implement the adapter once NTNU/TP provides its supported authorization
> and booking-access contract. No live student integration is shipped or claimed
> as verified by this change.

The demo and conversation store are intended for a single backend process. Demo
reservations are isolated sample inventories, not a simulation of contention
between all students. Conversation state expires after an hour; demo fixture files
are removed when expired sessions are pruned. A multi-worker or serverless live
deployment needs shared conversation/idempotency storage before activation.

## Running and checks

Use the existing [marketplace startup](../../marketplace/README.md). The backend
lockfile includes the local TP MCP package. Docker builds now use the repository
root as context and copy only the MCP package definition and source, excluding
local sessions and virtual environments. Environment names are documented in
[`backend/.env.example`](../../marketplace/backend/.env.example).

Checks from `marketplace/backend`: `uv run python -m unittest discover -s tests -q`.
Checks from `marketplace/frontend`: `pnpm typecheck` and `pnpm build`.
The original MCP test suite remains in `experiments/tp-room-booking-mcp/tests`.

Feature tests exercise MCP booking/cancellation across subprocesses, visitor
isolation, duplicate confirmation, missing information, live/demo separation,
browser mutation protection and trusted authorization redirects. The browser flow
was tested using sample rooms; real multi-student Feide/TP booking remains pending.
