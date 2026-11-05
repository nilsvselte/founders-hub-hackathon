---
name: marketplace-mcp
description: The marketplace MCP server that lets Claude and outside agents search, quote, and book rooms. Use when building or changing its tools, the per-user API token, or how outside "Bnb agents" connect.
---

# Marketplace MCP server

Status: **planned** (`marketplace/agent/mcp_server/server.py`). A small MCP server in front of the existing FastAPI backend. Claude Desktop or Code (on the Max subscription) runs it locally next to the Google Calendar connector; that pairing is the demo. The server holds no business rules: every tool calls a backend endpoint, and the backend decides availability, price, and confirmation.

## Tools

| Tool | Hint | Backend call | Status of endpoint |
| --- | --- | --- | --- |
| `search_rooms` | readOnly | `GET /rooms` (+ filters) | exists |
| `quote_room` | readOnly | `GET /rooms/{id}/quote` | exists |
| `suggest_rooms` | readOnly | `POST /suggestions` | planned |
| `get_preferences` | readOnly | `GET /me/preferences` | planned |
| `hold_room` | destructive | `POST /standby-requests` with `room_id` | exists |
| `confirm_booking` | destructive | `POST /standby-requests/{id}/offers/{offer_id}/accept` | exists |
| `list_bookings` | readOnly | `GET /bookings` | planned |
| `cancel_booking` | destructive | `DELETE /bookings/{ref}` | planned |

- Set `readOnlyHint` / `destructiveHint` annotations on every tool so the client asks before destructive ones.
- Destructive tools take the exact room, start, end, and max price the user approved. Where the client supports it, use elicitation to confirm partway through a call.
- Tool inputs carry time, length, headcount, and rough area only: no event titles, names, or emails.
- Tool results are plain JSON with prices in øre and timestamps with offsets.

## Auth: per-user token (planned)

Today `require_user` (`accounts.py`) accepts only a cookie session plus `x-marketplace-request: 1`. Add a bearer API token per account:

1. The user creates a token on the account page; store only its hash.
2. `require_user` accepts `Authorization: Bearer <token>` as well as the cookie.
3. The MCP server reads the token from its env (`MARKETPLACE_API_TOKEN` in `.env`), never from a file in the repo.
4. Revoking the token cuts off the agent.

## Outside "Bnb agents"

Any agent (a company assistant, a calendar tool, ChatGPT later) books through the same tools with the user's token, the way a travel agent books stays. It gets the same eligible openings, the same quotes, and the same hold-and-confirm rules as a human renter, and its booking still needs that user's yes. Hosting it publicly (remote MCP over HTTPS) is later and needs Håkon's go-ahead.

## Cost rule

The server runs locally and calls only our backend. Reasoning happens in the user's Claude chat on their subscription; keep `MARKETPLACE_DEMO_MODE=1` so the backend's own matcher makes no paid API calls.
