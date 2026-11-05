# Agentic platform

standbyroom is built so that agents, not just people, find and book meeting rooms. This page explains the agents, what they read, and where the human stays in control.

Code: the matcher is in [`marketplace/backend/app/matching.py`](../../marketplace/backend/app/matching.py), prices in [`pricing.py`](../../marketplace/backend/app/pricing.py), and the calendar-driven agent in [`marketplace/agent/`](../../marketplace/agent/).

## The core rule

Agents choose and explain. The marketplace owns availability, price limits, holds, and booking confirmation. The backend checks the slot and enforces the scope of the renter’s approval in either booking flow.

## Standby matching (built)

The first agent flow, live in the marketplace today:

1. The host schedules the room's occupied block. When staff press **Release room** on the Atech device during that block, the marketplace makes the remaining time available after a turnaround buffer.
2. A renter selects **Book when available** for one room or lets standbyroom look across venues. This authorizes a booking within the selected room scope, time window, duration, group size, equipment needs, and maximum total price.
3. The marketplace checks eligible openings, calculates the quote, and confirms the booking in the same transaction that reserves the slot. If another booking takes the opening, the request waits for another eligible match. Existing manual requests still show a held offer that the renter must accept.

The backend first filters openings to the ones that fit. Pydantic AI passes the eligible room, time, price, capacity, and equipment to Claude, which chooses an option with `propose_match` or returns `no_match`. The live matcher defaults to Claude Sonnet 5.5. Keyless demo mode picks the lowest-priced eligible opening deterministically. [Matcher setup](../../marketplace/README.md#try-the-booking-demo)

## Calendar assistant (local)

Claude uses its Google Calendar connector and the marketplace’s local stdio MCP server. Renters issue or revoke an assistant token from **Calendar assistant** at `/agent` and manage their profile, room preferences, and agent settings at `/account/preferences`.

1. The assistant looks for upcoming in-person meetings that need a room and passes the meeting slot, headcount, and an optional rough area to the marketplace. Calendar titles, attendee identities, and descriptions stay in the calendar tool.
2. Read-only suggestions rank up to three available options using the meeting criteria and the renter’s preferences. Each option includes the room, time, price, and a reason.
3. The renter approves a specific room, time, and maximum total price. The assistant uses the manual hold-and-confirm flow. A different option requires separate approval.

[Run the local assistant](../../marketplace/agent/README.md)

The assistant reads a compact account summary through `GET /me/agent-context`. It includes matching filters, preferences, and suggestion settings. It omits the renter’s name, email, account ID, and team name, and rounds saved coordinates to a rough area. When a standby request omits equipment or a budget, the backend uses saved defaults where available and preserves explicitly submitted values. [Account preferences](../../marketplace/agent/.agents/skills/preferences/SKILL.md)

## Agents that book through the marketplace (planned)

The marketplace is open to agents other than its own:

- **Bnb agent:** an agent that finds and books rooms for a person or team, the way a travel agent books stays. It searches listings, compares quotes, and books on the user's approval.
- **Outside agents:** third-party agents (a company assistant, a calendar tool, another person's AI) book via the marketplace's API. They get the same eligible openings, the same quotes, and the same hold-and-confirm rules as a human renter.

## What the agents use

### Sensor and occupancy data

Atech boards report presence through the [device server](../../device/README.md). The host dashboard shows the last reported occupancy and when it changed. An explicit staff release can open the remaining time on a scheduled room block.

**Planned:** use the device server's presence history and coverage to flag possible no-shows. Occupancy alone does not alter a booking.

### Dynamic prices

Each room has a base hourly rate and a minimum and maximum set by the host. The marketplace adjusts the rate by when the booking starts (weekday peak, off-peak, weekend) and gives a last-minute discount for starts within 30 minutes, always clamped to the host's limits. Every quote carries a plain-language reason. Agents compare quotes against the user's budget and can point out a cheaper nearby slot; they never set prices themselves.

## Calendar connection

- **Claude connector:** Claude reads calendar events in the renter’s chat and calls the local marketplace tools for suggestions and approved bookings.
- **Local scan:** a renter can preview eligible meetings from a local `.ics` export. The scanner checks the next seven days for timed meetings of at least 15 minutes with two or more people and no room, physical location, or video link. Its output contains meeting times, headcount, and an optional area.
- **Add to Google Calendar:** confirmed marketplace bookings open a prefilled event draft that the renter can save.

**Planned:** product-managed Google OAuth, scheduled calendar scans, and live write-back to existing events. The local helper prepares an update that keeps the event’s times and attendees and adds the room location and reference without notifying attendees. The marketplace does not submit the update today.

How-to: [`calendar-scan`](../../marketplace/agent/.agents/skills/calendar-scan/SKILL.md), [`calendar-write-back`](../../marketplace/agent/.agents/skills/calendar-write-back/SKILL.md).

## Agent capabilities

What an agent can do through the marketplace, and what exists today:

| Action | Approval | Today |
| --- | --- | --- |
| Search rooms, get a quote | none (read-only) | built: `GET /rooms`, `GET /rooms/{id}/quote` |
| Suggest up to three rooms for a meeting | none (read-only) | built: `POST /suggestions` |
| Read matching preferences and agent context | none (read-only) | built: `GET /me/agent-context` |
| Read or edit account preferences | renter uses `/account/preferences` | built: `GET/PUT /me/preferences` |
| Automatically confirm a matching opening | renter chooses **Book when available** with limits | built: renter standby request |
| Hold and book a suggested room | renter approves that room, time, and price | built: local MCP `hold_room` and `confirm_booking` |
| List bookings | none (read-only) | built: local MCP `list_bookings` |
| Cancel bookings | renter approves cancellation | planned |

The local MCP server uses a per-renter token and marks search, quotes, suggestions, and history as read-only. Hold and confirmation request explicit approval. In the keyless calendar demo, Claude reasons in the renter’s chat and the marketplace uses deterministic matching.

How-to: [`marketplace/agent/AGENTS.md`](../../marketplace/agent/AGENTS.md) and its skills [`preferences`](../../marketplace/agent/.agents/skills/preferences/SKILL.md), [`room-matching`](../../marketplace/agent/.agents/skills/room-matching/SKILL.md), [`booking`](../../marketplace/agent/.agents/skills/booking/SKILL.md), [`marketplace-mcp`](../../marketplace/agent/.agents/skills/marketplace-mcp/SKILL.md).
