# Agentic platform

standbyroom is built so that agents, not just people, find and book meeting rooms. This page explains the agents, what they read, and where the human stays in control.

Code: the matcher is in [`marketplace/backend/app/matching.py`](../../marketplace/backend/app/matching.py), prices in [`pricing.py`](../../marketplace/backend/app/pricing.py), and the calendar-driven agent in [`marketplace/agent/`](../../marketplace/agent/).

## The core rule

Agents choose and explain; the marketplace decides. Availability, price limits, holds, and booking confirmation live in the marketplace backend, so every agent works from the same rules as the website. An agent never books on its own say-so: the backend rechecks the slot and confirms.

## Standby matching (built)

The first agent flow, live in the marketplace today:

1. When a room is ready, a staff member presses **Release room** on an Atech device. The marketplace makes the remaining time available after a turnaround buffer.
2. A buyer leaves a standby request: time window, duration, group size, equipment needs, budget, and any flexibility. A Claude agent checks available slots and matches the request to a room as openings come in.
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

Atech boards in each room report presence to the device server, which exposes occupancy to the marketplace (contract: [device/README.md](../../device/README.md)). Agents use it to:

- learn about openings the moment a room empties or staff press **Release room**, instead of waiting for the booked block to end;
- spot ghost bookings: a booked room that stays empty can be released and offered on;
- trust a suggestion: an agent can say a room is free now, not just free on paper.

The device server reports facts; the marketplace decides what they mean for bookings.

### Dynamic prices

Each room has a base hourly rate and a minimum and maximum set by the host. The marketplace adjusts the rate by when the booking starts (weekday peak, off-peak, weekend) and gives a last-minute discount for starts within 30 minutes, always clamped to the host's limits. Every quote carries a plain-language reason. Agents compare quotes against the user's budget and can point out a cheaper nearby slot; they never set prices themselves.

## Calendar connection

> TODO: research in progress. Will cover which calendars the agent connects to, how access is granted and scoped, what event data it reads, and how it finds meetings without a room.

## Agent capabilities

> TODO: research in progress. Will cover the actions agents can take through the marketplace (search, quote, hold, book, cancel), the API outside agents use, how they authenticate, and the approval step for each action.
