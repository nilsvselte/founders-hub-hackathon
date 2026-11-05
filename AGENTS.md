# Mesh meeting room standby market

Mesh has meeting room time it can sell to the public. When a meeting ends early, the remaining time is hard to sell before it expires. We’re building a self-service marketplace that turns those openings into bookings at Digs in Trondheim.

1. When a room is ready, a staff member presses **Release room** on an Atech device. The marketplace makes the remaining time available after a turnaround buffer.
2. A buyer leaves a standby request with their time window, duration, group size, equipment needs, budget, and any flexibility. A Claude agent checks available slots and matches the request to a room as openings come in.
3. The marketplace calculates a quote within Mesh’s pricing limits and holds the slot. The buyer accepts the quote, and the marketplace rechecks availability before confirming the booking. If the slot disappears, the agent looks for the next viable option.

## Repository layout

| Folder | Owns |
| --- | --- |
| `website/` | Public landing page that explains the product and directs buyers to the marketplace. |
| `marketplace/frontend/` | Next.js app for buyers to submit standby requests and accept offers. |
| `marketplace/backend/` | FastAPI app served by Uvicorn. Owns inventory, pricing, holds, booking, and the Claude agent’s tools. Uses PostgreSQL. |
| `device/` | Atech ESP32 firmware and code that passes the button press to the marketplace. This folder starts empty. |

## Hackathon demo

Use one physical button, two sample rooms, and one standby request. Show that the buyer has no matching slot, press **Release room**, then show the agent find a match and quote it. Accept the offer and show a confirmed test booking.

Keep availability, price limits, and booking confirmation in the marketplace so the agent works from the same rules as the rest of the product. Edit this guide directly. `CLAUDE.md` links to it.

See the [marketplace README](marketplace/README.md) for local startup commands.
