# standbyroom live demo

A renter asks for a room. A host releases unused time. Claude finds a match, and standbyroom confirms the booking within the renter’s approved limits.

## Before the audience arrives

1. Start the marketplace API on `8001` and the frontend on `3001`, with `MARKETPLACE_API_URL=http://127.0.0.1:8001`. Serve the landing page from the repo root with `python3 -m http.server 8088 --bind 127.0.0.1 --directory website`. Open the [landing page](http://127.0.0.1:8088/) and [host dashboard](http://127.0.0.1:3001/host) in separate sessions, and check [API readiness](http://127.0.0.1:3001/api/ready). [Marketplace setup](README.md)
2. In a test database, publish a fresh host-owned room with a screen and capacity for four. Keep the demo window clear of existing openings. Sign in as the host and as two separate test renters. Configure the live matcher and confirm a rehearsal booking shows **Matched by Claude**. Use fresh inventory for the stage run. [Live matcher setup](README.md#try-the-booking-demo)
3. Pick an exact 30-minute slot starting about 10 minutes into the future. Choose a total budget above the rehearsed price. A one-hour release covers this window and the default two-minute turnaround.

For a Digs fixture, enable `MARKETPLACE_DEMO_MODE=1` on a disposable Compose stack. Set `DEMO_HOST_PASSWORD` locally to at least 12 characters for a new account. Run this from `marketplace/` to give the test host ownership of the unowned Digs rooms, including Driv (`digs-demo-1`).

```sh
docker compose exec -e DEMO_HOST_PASSWORD="$DEMO_HOST_PASSWORD" api .venv/bin/python -m app.demo_host host@example.test
```

Compose serves the marketplace on `3000`. For Compose or a hosted HTTPS preview, set `data-marketplace-origin` on the landing page’s `main.js` script tag to the matching marketplace origin. To show the installable phone app separately, open that HTTPS preview on the phone. [Phone app setup](../docs/phone-app.md)

**Live demo room link.** `DEMO_ROOM_ID` in `frontend/app/demo-room.tsx` sets the room behind every **Live demo room** link (now `digs-demo-1`). Change that one line when the physical room is ready.

## On stage

| Show | Say and do |
| --- | --- |
| **Landing page → standby request** | Choose the meeting date and four people on the static landing page. Continue to the marketplace. Enter the rehearsed earliest start and latest end, 30 minutes, a screen, and a maximum total price. Point to the booking authorization and select **Book when available**. |
| **Waiting for an opening** | Show the renter waiting. In the host dashboard, find the test listing, choose **1 hour** under **Available from now**, and select **Release time**. |
| **Booking confirmed** | Return to the renter tab. Show **Matched by Claude**, the room, exact time, final price, and booking reference. The booking is confirmed for the slot after the turnaround buffer. |
| **Slot taken and Calendar draft** | In the second renter session, request the same room for the exact confirmed interval. Check that it stays on standby without an offer. On the first booking, open **Add to Google Calendar** to show the prefilled event draft. |

## Optional host and device view

The host dashboard refreshes about every 12 seconds. It shows **Booked until**, **Blocked until**, or **Free now** alongside **Occupied since**, **Empty since**, or **No sensor**. A current booking or block with a reported empty room gets a warning after 10 minutes. Occupancy reports update the badge. A teammate can demonstrate a connected board’s **Release room** button during an active host block. Use **Release time** for the main demo so the booking does not depend on the board or WiFi. [Device setup](../device/README.md)

**Live room view (no sign-in).** Open `/live/digs-demo-1` on the marketplace (local: http://127.0.0.1:3001/live/digs-demo-1) on the projector or a phone. It polls `GET /public/rooms/digs-demo-1/live` every 2 s and shows **Someone’s in the room**, **Empty** or **No sensor** with the last sensor reading time, **Booked**/**Blocked**/**Free now** with the current time span, and the booked-but-empty warning. Only venue demo rooms are public; no booking references or names are returned. The sensor feeds it through `POST /internal/device/events` (bearer `MARKETPLACE_DEVICE_TOKEN`) with `{"type":"room.occupancy_changed","event_id":"<unique>","external_room_id":"digs-demo-1","occupied":true,"changed_at":"<ISO time with offset>"}`. Every event needs a new `event_id` and a `changed_at` later than the last one.

## Rehearsal checklist

- Use a fresh listing or a fresh meeting window per run. Record the transition from waiting to confirmed and compare the final price with the renter’s maximum total.
- Verify the competing request receives no offer and the Calendar link carries the confirmed room, time, and reference. Keep the Calendar draft unsaved.
- For a keyless rehearsal, set `MARKETPLACE_DEMO_MODE=1` and leave `ANTHROPIC_API_KEY` unset. Expect **Demo match** and describe it as the deterministic demo. Keep simulated board events separate from physical hardware results.

## Rehearsal on 5 November 2026

All 100 isolated host-release cycles on `8409dbc` passed with live Claude Sonnet. The 99 API runs and one full browser run produced 100 distinct booking references, zero fallback matches, and zero double bookings for the same room and time.

The browser run verified the landing page handoff, the waiting request, host release, automatic confirmation, and the exact time, Oslo time zone, room, and reference in the Google Calendar draft link. No event was saved. This rehearsal used the host dashboard release and did not exercise the physical board.
