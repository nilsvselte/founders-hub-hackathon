# standbyroom in 90 seconds

Before presenting, sign in with a renter account and open [Driv at Mesh’s Digs venue](http://127.0.0.1:3000/rooms/digs-demo-1). Keep [Kowork’s shared meeting room](http://127.0.0.1:3000/rooms/kowork-meeting-room) as a second example. Use a fresh test session with a room that has no current opening if you want to show the waiting state.

| Time | On screen |
| --- | --- |
| 0–25 s | Show Driv’s listing. In **Price estimate**, select **30 min** and compare **Weekday morning**, **Weekday evening**, and **Weekend**. The demo catalog’s NOK 450 hourly rate gave NOK 270, NOK 191.25, and NOK 180 respectively when checked for starts more than 30 minutes away. Read the current estimate aloud if rates change. |
| 25–45 s | Under **Request this room**, use the default two-hour window, 30 minutes, four people, and the default budget. Select **Book when available** and show **Waiting for an opening**. The request authorizes a booking within those limits. |
| 45–90 s | Press **Release room** on the device during a scheduled block, or select **Release demo room** to simulate it. Watch standbyroom match and confirm the booking. Show the reference, final price, and **Add to Google Calendar**. If the room was already available, repeat with a room that has no active opening. |

## Host view: live room status

The host dashboard at [/host](http://127.0.0.1:3000/host) shows each room as **Booked until HH:MM**, **Blocked until HH:MM** or **Free now**, and the sensor as **Occupied** or **Empty since HH:MM**, or **No sensor**. A room that is booked but has been empty for 10 minutes gets a **Booked but empty** warning. The page refreshes every 12 seconds.

To give a demo host the Mesh/Digs rooms (Driv, Gnist), start the stack with `MARKETPLACE_DEMO_MODE=1` and run this once from `marketplace/`. Pick any test email and a password of 12+ characters; keep both out of the repo.

```sh
docker compose exec -e DEMO_HOST_PASSWORD='<password>' api .venv/bin/python -m app.demo_host <host email>
```

It creates the host account if needed and assigns every unowned Digs room to it; running it again is harmless. Sign in at `/sign-in` with that email, in a separate browser session from the renter. Owned rooms no longer receive catalog migrations that only touch unowned rooms.

To see a sensor change without the board, post an event with the device token from `marketplace/.env`:

```sh
curl -X POST http://127.0.0.1:8000/internal/device/events -H "Authorization: Bearer $MARKETPLACE_DEVICE_TOKEN" -H 'Content-Type: application/json' \
  -d "{\"type\":\"room.occupancy_changed\",\"event_id\":\"$(uuidgen)\",\"external_room_id\":\"digs-demo-1\",\"occupied\":false,\"changed_at\":\"$(date -u +%FT%TZ)\"}"
```

Hosts can also create and publish their own listing, then select **Release time**. A renter can request that published listing from a separate browser session.

Docker Compose serves the app on port **3000**. Start the test backend with `MARKETPLACE_DEMO_MODE=1`, leave `ANTHROPIC_API_KEY` unset, and verify `/api/ready` and `/api/demo/config` on the frontend origin. The keyless matcher labels the result **Demo match**. Use a demo-enabled API and test database for Vercel previews. [Local setup](README.md) · [Preview deployment](DEPLOYMENT.md)

To show the separate calendar flow, use a test calendar with an upcoming in-person meeting that needs a room. Open **Calendar assistant**, follow the [local MCP setup](agent/README.md), and ask Claude for room suggestions. Approve the displayed room, time, and price to book it. This approval step is specific to the assistant flow.
