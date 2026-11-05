# standbyroom meeting room marketplace

Renters can browse venues, sign in, and request a time. Hosts use a separate dashboard to create and publish room listings and release availability. When an opening matches a request, the marketplace holds a priced offer and confirms it after the renter accepts. Next.js serves the marketplace and FastAPI on Uvicorn manages accounts and bookings in PostgreSQL.

## Run with Docker Compose

With Docker and the Compose plugin installed, start the Docker engine. Run this from `marketplace/`.

```sh
docker compose up --build -d --wait
```

Open [the marketplace](http://127.0.0.1:3000) or [the API docs](http://127.0.0.1:8000/docs). Compose waits for PostgreSQL, the API, and the frontend’s `/api/ready` route. You can check the full connection with `curl -f http://127.0.0.1:3000/api/ready`.

Run the same Compose command after editing the app to rebuild the images. Use `docker compose down` to stop the stack. PostgreSQL data stays in a named volume.

## Develop with hot reload

Use Node.js 22 or newer with pnpm 11, and Python 3.12 or newer with uv. If the full Compose stack is running, stop it first to free ports 3000 and 8000.

### Start PostgreSQL

Run this from `marketplace/`.

```sh
docker compose up -d --wait db
```

PostgreSQL listens on `127.0.0.1:5432` and stores data in a named volume. If you already have a PostgreSQL server, use its connection URL in the next step and skip Compose.

### Start the API

Run these from `marketplace/backend/`.

```sh
cp .env.example .env
uv sync --locked
uv run --locked --env-file .env uvicorn app.main:app --reload
```

The API serves OpenAPI docs at `http://127.0.0.1:8000/docs`. `GET /health` checks the process. `GET /ready` runs a PostgreSQL query and returns HTTP 503 if the database is unavailable.

### Start the frontend

Run these from `marketplace/frontend/`.

```sh
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000`. Next.js forwards `/api/*` to Uvicorn so browser requests use the same origin. Run `curl -f http://localhost:3000/api/ready` to check the connection through the frontend. To use a different API address, copy `.env.example` to `.env.local` in the frontend and set `MARKETPLACE_API_URL` before starting or building Next.js.

## Try the booking demo

1. Set `MARKETPLACE_DEMO_MODE=1` in `backend/.env` before starting Uvicorn.
2. Create a renter account, open a sample room, and submit a standby request. Press the demo release control to simulate an early release for that room.
3. Wait for the quote, then accept it. The marketplace shows a booking reference once PostgreSQL confirms the reservation.

Set `ANTHROPIC_API_KEY` in the backend environment to use Claude. You can override the model with `ANTHROPIC_MODEL`. Without a key, demo mode uses a deterministic matcher and labels its offers as demo matches. Keep demo mode disabled outside local development.

To test the host side, register as a host, create a listing, publish it, and release an opening from the host dashboard. Use a separate browser session to book it as a renter.

## Pilot venues

The public catalog shows published listings across venues. A room-specific standby request can only match an opening for that room. For the venue API and default room used by a demo release without an explicit room ID, set `MARKETPLACE_VENUE` to `digs` (Mesh at Digs, the default), `kowork` (Kowork at Kjøpmannsgata 40 in Trondheim), or `brighten` (Brighten at Bakke Bydelshus, Nordre Berggate 2).

To use Kowork as the default pilot in Docker Compose, run this from `marketplace/`.

```sh
MARKETPLACE_VENUE=kowork MARKETPLACE_DEMO_MODE=1 docker compose up --build -d --wait
```

The Kowork seed includes the shared meeting room, listed for groups of 8 to 12, and a quiet room. The capacity information comes from [Koteng](https://koteng.no/). The equipment and prices are sample values pending confirmation from Kowork. The catalog uses Kowork’s own meeting-room photo from [Koteng](https://koteng.no/). See [the venue migration](backend/app/migrations/002_venues.sql).

Brighten lists a meeting room and a phone pod. Their capacities, equipment, and prices are placeholders until Brighten confirms them. The catalog uses Brighten’s meeting-room photo from [Brighten](https://brighten.no/).

Mesh’s Digs listings use Mesh Community’s room photography for Driv and its shared Gnist and Spark gallery. Listings without a verified image are shown without a room photograph. [Mesh Community’s Trondheim room gallery](https://meshcommunity.com/trondheim/meeting-event)

Research for 26 additional Trondheim and Stjørdal venues is stored as unpublished listings. The customer roster should confirm a venue before its rooms are published. Unpublishing these research listings preserves existing booking history. [Catalog research](backend/app/migrations/011_trondheim_venue_catalog.sql) · [Draft migration](backend/app/migrations/012_keep_unconfirmed_venue_leads_unpublished.sql)

## Run backend checks

From `marketplace/backend/`, run `uv run --locked python -m unittest discover -s tests -v`. Set `MARKETPLACE_TEST_DATABASE_URL` to a disposable PostgreSQL database to include the concurrent booking checks.

## Connect a device

Set `MARKETPLACE_DEVICE_TOKEN` to enable `POST /internal/device/events`. The device integration sends `Authorization: Bearer <token>`. For local testing, the fixture adapter accepts `type: room.released`, `event_id`, `external_room_id`, `block_id`, `released_at`, and `scheduled_end_at`. Pilot room IDs are `digs-demo-1` and `digs-demo-2` for Digs, `kowork-meeting-room` and `kowork-quiet-room` for Kowork, and `brighten-meeting-room` and `brighten-phone-pod` for Brighten. Send both timestamps as ISO 8601 strings with offsets, and reuse event and block IDs when retrying the same release.

When the real API is ready, set `MARKETPLACE_DEVICE_ADAPTER` to a trusted Python factory path such as `app.vendor_device:create_adapter`. The factory implements `DeviceAdapter` in `backend/app/device.py`. A webhook or a poller can pass the provider payload through the same adapter. The adapter supplies a source, stable IDs, and the release window. The backend handles deduplication, availability, quotes, and booking.
