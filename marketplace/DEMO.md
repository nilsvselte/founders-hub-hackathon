# Roomline in 90 seconds

Before presenting, sign in with a renter account and open [Driv at Mesh’s Digs venue](http://127.0.0.1:3001/rooms/digs-demo-1). Keep [Kowork’s shared meeting room](http://127.0.0.1:3001/rooms/kowork-meeting-room) as a second example. Use a fresh test session with a room that has no current opening if you want to show the waiting state.

| Time | On screen |
| --- | --- |
| 0–25 s | Show Driv’s listing. In **Price estimate**, select **30 min** and compare **Weekday morning**, **Weekday evening**, and **Weekend**. The demo catalog’s NOK 450 hourly rate gave NOK 270, NOK 191.25, and NOK 180 respectively when checked for starts more than 30 minutes away. Read the current estimate aloud if rates change. |
| 25–45 s | Under **Request this room**, use the default two-hour window, 30 minutes, four people, and the default budget. Select **Send request** and show **Waiting for an opening**. The estimate above is a comparison and the request form sets the actual booking window. |
| 45–90 s | Select **Release demo room** to simulate the host’s release button. Watch the offer appear, then select **Accept and book** before the hold expires. Show the booking reference and the final price. If an offer was already available, use a room without an active opening to demonstrate the release. |

For the host view, sign in with a separate host account. Create and publish a test listing, then select **Release time**. A renter can request that published listing from a separate browser session.

The current local preview uses port **3001**. Docker Compose uses **3000** by default. Start the test backend with `MARKETPLACE_DEMO_MODE=1` and verify `/api/ready` and `/api/demo/config` on the frontend origin. Configure `ANTHROPIC_API_KEY` on the backend if you want to show Claude matching. Without the key, demo mode labels the offer **Demo match**. For Vercel, use a test preview URL connected to a demo-enabled API and test database. See [local setup](README.md) and [preview deployment](DEPLOYMENT.md).
