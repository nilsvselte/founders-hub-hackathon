# standbyroom meeting room marketplace

standbyroom is a marketplace for meeting rooms across venues. Renters browse listings and request a time. Hosts manage their rooms and can release unused time. Mesh and Digs are the original pilot context.

1. When a room is ready, a staff member presses **Release room** on an Atech device. The marketplace makes the remaining time available after a turnaround buffer.
2. A buyer leaves a standby request with their time window, duration, group size, equipment needs, budget, and any flexibility. A Claude agent checks available slots and matches the request to a room as openings come in.
3. The marketplace calculates a quote within the room’s pricing limits and holds the slot. The renter accepts the quote, and the marketplace rechecks availability before confirming the booking. If the slot disappears, the agent looks for the next viable option.

## Repository layout

| Folder | Owns |
| --- | --- |
| `website/` | Public landing page that explains the product and directs buyers to the marketplace. |
| `marketplace/frontend/` | Next.js marketplace for browsing rooms, renter bookings, and host listings. |
| `marketplace/backend/` | FastAPI app served by Uvicorn. Owns accounts, inventory, pricing, holds, bookings, and the Claude agent’s tools. Uses PostgreSQL. |
| `device/` | Atech ESP32 firmware and code that passes the button press to the marketplace. This folder starts empty. |

## Hackathon demo

Use one physical button, two sample rooms, and one standby request. Show that the buyer has no matching slot, press **Release room**, then show the agent find a match and quote it. Accept the offer and show a confirmed test booking.

Keep availability, price limits, and booking confirmation in the marketplace so the agent works from the same rules as the rest of the product. Edit this guide directly. `CLAUDE.md` links to it.

The device API contract is still open. Put its translation behind `DeviceAdapter` in the marketplace backend. A fixture drives the same release flow locally. Claude chooses among eligible openings and explains the fit. The backend controls the quote, hold, and booking.

See the [marketplace README](marketplace/README.md) for local startup commands.
