# Agentic platform

standbyroom is built so that agents, not just people, find and book meeting rooms. This page explains the agents, what they read, and where the human stays in control.

Code: the matcher is in [`marketplace/backend/app/matching.py`](../../marketplace/backend/app/matching.py), prices in [`pricing.py`](../../marketplace/backend/app/pricing.py), and the calendar-driven agent in [`marketplace/agent/`](../../marketplace/agent/).

## The core rule

Agents choose and explain; the marketplace decides. Availability, price limits, holds, and booking confirmation live in the marketplace backend, so every agent works from the same rules as the website. An agent never books on its own say-so: the backend rechecks the slot and confirms.

## Standby matching (built)

The first agent flow, live in the marketplace today:

1. The host schedules the room's occupied block. When staff press **Release room** on the Atech device during that block, the marketplace makes the remaining time available after a turnaround buffer.
2. A buyer leaves a standby request for one room or lets standbyroom look across venues. The request includes a time window, duration, group size, equipment needs, budget, and any flexibility. The marketplace checks available slots as openings come in.
3. The marketplace calculates a quote within the room's pricing limits and holds the slot. The renter accepts the quote, and the marketplace rechecks availability before confirming the booking. If the slot disappears, the agent looks for the next viable option.

The backend first filters openings down to the ones that fit. Claude then sees only those validated options (room, time, price, capacity, equipment; no database IDs) and calls one of two tools: `propose_match` (pick one, explain the fit in a sentence) or `no_match`. Without an API key, demo mode uses a deterministic matcher instead.

## The marketplace agent (planned)

A personal agent that works ahead of you instead of waiting for a request:

1. **Reads your calendar** and finds upcoming meetings that have no room.
2. **Suggests a room** for each one, weighing:
   - attendees: how many, and where they are coming from;
   - location: close to the attendees or to where you will be before and after;
   - time: the meeting's slot and any slack around it;
   - your preferences: price ceiling, favourite venues, equipment, quiet vs. social.
3. **Asks you to approve.** You see the room, the price, and why it fits. Nothing is booked until you say yes; then the marketplace holds and confirms the slot as above.

It lives in [`marketplace/agent/`](../../marketplace/agent/).

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

## Calendar connection (planned)

The marketplace agent reads Google Calendar in one of three ways:

- **Assistant mode (demo):** the user's own Claude chat with the Google Calendar connector reads and updates events. Free on the subscription, but it works only inside that user's chat.
- **ICS link:** the calendar's secret iCal address, read by the backend. Read-only and free; the link exposes the whole calendar, so the demo uses a throwaway account.
- **Google OAuth:** read scope `calendar.events.readonly`, write scope `calendar.events` asked for only at first booking. Gives event ids and lets the agent write the booked room back. Microsoft 365 via Graph comes later.

A meeting **needs a room** when it is upcoming, timed (not all-day), at least 15 minutes, has 2+ people, the user has not declined it, and it has no room resource, no physical location, and no video link. Only start time, length, headcount, and a rough area leave the user's side; titles, names, and emails stay private. After booking, the agent writes the room's address into the event's location and the booking ref into its description, without notifying attendees.

How-to: [`calendar-scan`](../../marketplace/agent/.agents/skills/calendar-scan/SKILL.md), [`calendar-write-back`](../../marketplace/agent/.agents/skills/calendar-write-back/SKILL.md).

## Agent capabilities

What an agent can do through the marketplace, and what exists today:

| Action | Approval | Today |
| --- | --- | --- |
| Search rooms, get a quote | none (read-only) | built: `GET /rooms`, `GET /rooms/{id}/quote` |
| Suggest top 3 rooms for a meeting | none (read-only) | planned: `POST /suggestions` |
| Read or set preferences (price ceiling, room types, equipment, venues) | user edits them | built: `GET/PUT /me/preferences`; the agent reads `GET /me/agent-context` |
| Hold and book a room | user's yes to that room, time, and price | built: standby request → offer → accept |
| List or cancel bookings | user's yes to cancel | planned |

Agents reach these through a **marketplace MCP server** (planned) in front of the backend. Read-only tools are marked read-only; hold, book, and cancel are marked destructive so the client asks first. An agent signs in with a per-user API token the user can revoke, and outside agents ("Bnb agents") get the same openings, quotes, and rules as a human renter. There are no payments, and the agent's reasoning runs in the user's own Claude chat, so the marketplace makes no paid model calls.

How-to: [`marketplace/agent/AGENTS.md`](../../marketplace/agent/AGENTS.md) and its skills [`preferences`](../../marketplace/agent/.agents/skills/preferences/SKILL.md), [`room-matching`](../../marketplace/agent/.agents/skills/room-matching/SKILL.md), [`booking`](../../marketplace/agent/.agents/skills/booking/SKILL.md), [`marketplace-mcp`](../../marketplace/agent/.agents/skills/marketplace-mcp/SKILL.md).
