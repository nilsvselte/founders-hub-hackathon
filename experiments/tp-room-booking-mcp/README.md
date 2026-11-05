# Experimental NTNU TP room-booking MCP

A standalone experiment for agents to find and book NTNU rooms. Uses the official
MCP Python SDK over stdio. It does not depend on the Roomline backend or database.

**The fixture backend works end to end. The live backend has passed public read
checks; authenticated availability and real booking/cancellation are not yet
verified.** No real reservations were made during development.

## Run the experiment

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd experiments/tp-room-booking-mcp
uv sync --frozen --no-editable --extra dev --extra login
.venv/bin/tp-room-booking-mcp
```

The server defaults to `TP_BACKEND=fixture`. It waits for MCP messages on stdin;
it is not an interactive terminal chat. Attach it to an MCP client using the
configuration below, or run `.venv/bin/python scripts/demo.py` for a complete demo.
Fixture rooms and booking IDs start with `DEMO-`. Fixture state lives only in the
server process and resets when it exits. It never reads a live session file or
makes network requests. It models room overlap, not NTNU's full policy rules.

## Attach to an agent

For an MCP client supporting a `mcpServers` JSON configuration, replace the path
with your checkout's **absolute** path after installing the dependencies:

```json
{
  "mcpServers": {
    "ntnu-tp-experiment": {
      "command": "/absolute/path/to/experiments/tp-room-booking-mcp/.venv/bin/tp-room-booking-mcp",
      "env": {
        "TP_BACKEND": "fixture"
      }
    }
  }
}
```

Try: “Find a demo room for eight people on 1 December 2026 from 12:00 to
13:00 Oslo time, book it as MCP experiment, list my bookings, then cancel it.”
Use a future date if this example is old. Every response identifies its backend.

| Tool | Purpose |
| --- | --- |
| `session_status` | Backend, authentication status and write setting |
| `list_locations` | Area/campus and building IDs |
| `search_available_rooms` | Directly bookable rooms filtered by time, size and location |
| `list_my_bookings` | Current user's reservation records |
| `get_booking_quotas` | Current user's TP quota response |
| `book_room` | One room and one time window, with an availability recheck |
| `cancel_booking` | Cancel an ID returned by the current user's bookings |

## Live TP mode

1. Run `.venv/bin/tp-room-booking-login`. It opens an installed Google Chrome browser.
   Sign in through Feide yourself and complete any MFA. Press Enter in the
   terminal once TP is visible. Use `--channel msedge` for installed Edge.
   The helper does not read or store your password. It saves only TP cookies to
   `.state/session.json`, with owner-only file permissions. That folder is ignored
   by Git. No browser download is required when using an installed browser.
2. Run the read-only probe:

   ```bash
   .venv/bin/tp-room-booking-probe \
     --start 2026-11-06T12:00:00+01:00 \
     --end 2026-11-06T13:00:00+01:00
   ```

3. Change your MCP client environment to:

   ```json
   {
     "TP_BACKEND": "tp",
     "TP_STATE_FILE": "/absolute/path/to/experiments/tp-room-booking-mcp/.state/session.json",
     "TP_ALLOW_WRITES": "1"
   }
   ```

   Omit `TP_ALLOW_WRITES` to try live searches without creating or cancelling
   reservations. Restart/reconnect your MCP client after changing its environment.

The login helper and server must use the same absolute `TP_STATE_FILE` when their
working directories differ. Renew expired sessions by running the login helper
again; a changed file is reloaded on the next request. Delete the state file to
remove the server's saved session access.

The MCP server can **actually submit** reservations in live mode with writes
enabled. TP remains responsible for permissions, booking windows, capacity and
quotas. Do not retry an uncertain write automatically: use `list_my_bookings` to
check its result first. There is no built-in scheduler or bulk booking behavior.

## How the live integration works

TP publishes [Swagger UI](https://tp.educloud.no/ntnu/ws/swagger-ui/dist/) and an
[OpenAPI document](https://tp.educloud.no/ntnu/ws/openapi.json). That document
describes an API-key booking interface under `/ws/roombooking/`.

The current website instead calls `/ws/rombestilling/` using the signed-in web
session and a different payload. This experiment follows those current frontend
calls, discovered in the public app bundle on 5 November 2026. It does **not**
assume an institutional API key is available. See [discovery notes](docs/discovery.md)
for the verified endpoints, wire formats and remaining gaps.

The login helper uses a browser only for interactive sign-in. MCP tools use HTTP
requests. Cookies are scoped to TP, cookie expiry/path rules are respected, and
the adapter mirrors Axios's `XSRF-TOKEN` → `X-XSRF-TOKEN` behavior when present.
It never follows an API redirect into a login page or retries a write.

Supported scope: one directly bookable room, one time window, own bookings and
cancellation. Recurring reservations, exams, application-only rooms, individual
seats, QR/check-in and editing are not implemented. Times without an offset mean
Europe/Oslo; offset timestamps are converted. Ambiguous DST transition hours are
rejected because TP's frontend sends offset-free wall-clock timestamps.

## Checks

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Tests cover the actual MCP subprocess protocol, fixture booking lifecycle,
overlap, filters, TP payloads, lost responses without automatic retries, ownership
checks, failed confirmation handling, cookie scoping/expiry and Oslo time handling.
All test HTTP responses are synthetic. The read-only probe is the explicit live
check; the test suite never contacts TP.
