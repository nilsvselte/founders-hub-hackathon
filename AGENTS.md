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
| `device/` | Atech ESP32 sensors (presence, CO₂, buttons) and a FastAPI device server that tracks room occupancy and exposes it to the marketplace. See [device/README.md](device/README.md). |

## Hackathon demo

Use one physical button, two sample rooms, and one standby request. Show that the buyer has no matching slot, press **Release room**, then show the agent find a match and quote it. Accept the offer and show a confirmed test booking.

Keep availability, price limits, and booking confirmation in the marketplace so the agent works from the same rules as the rest of the product. Edit this guide directly. `CLAUDE.md` links to it.

Claude chooses among eligible openings and explains the fit. The backend controls the quote, hold, and booking.

## Device integration

The device API contract is defined in [device/README.md](device/README.md). `device/` reports physical facts: whether a room is occupied, since when, and whether a staff member pressed **Release room**. It does not know about bookings. The marketplace owns bookings and decides on no-shows, overstays, auto-release, and pricing.

- **Push:** the device server posts `room.occupancy_changed` and `room.release_requested` to the existing `POST /internal/device/events`. The marketplace should handle both types behind `DeviceAdapter`. It maps a release request to the room's current block, and it can treat an empty room during a booked block as a ghost-booking signal.
- **Pull:** the marketplace can call the device server on port 8100. `GET /v1/rooms/{room_id}` returns current occupancy, and `GET /v1/rooms/{room_id}/presence?from=&to=` reports whether anyone was in the room during a booking window. Check `coverage` before treating an empty window as a no-show.

Room IDs are shared, so the device server uses the marketplace's room IDs, such as `digs-demo-1`.

See the [marketplace README](marketplace/README.md) for local startup commands.
