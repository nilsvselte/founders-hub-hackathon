# Mesh meeting room marketplace

Mesh buyers can leave a standby request for a meeting room. When staff release an opening, the marketplace matches the request, holds a priced offer, and confirms the booking after the buyer accepts. Next.js serves the buyer page, and FastAPI on Uvicorn handles matching and booking in PostgreSQL.

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
2. Submit a standby request on the buyer page, then press **Release demo room** in the demo controls. The control simulates an early release for a seeded room.
3. Wait for the quote, then accept it. The marketplace shows a booking reference once PostgreSQL confirms the reservation.

Set `ANTHROPIC_API_KEY` in the backend environment to use Claude. You can override the model with `ANTHROPIC_MODEL`. Without a key, demo mode uses a deterministic matcher and labels its offers as demo matches. Keep demo mode disabled outside local development.

## Choose a venue

Each deployment serves one venue, set with `MARKETPLACE_VENUE` in the backend. Use `digs` for Mesh at Digs (the default), `kowork` for Kowork at Kjøpmannsgata 40, or `brighten` for Brighten at Bakke Bydelshus, Nordre Berggate 2. The venue sets the page branding, the rooms that requests can match, the demo release room, and the booking reference prefix. Rooms and requests store their venue, so several venues can share one database.

To run the Kowork demo with Docker Compose, run this from `marketplace/`.

```sh
MARKETPLACE_VENUE=kowork MARKETPLACE_DEMO_MODE=1 docker compose up --build -d --wait
```

Kowork has a shared meeting room for 8 to 12 people and a quiet room, seeded in `backend/app/migrations/002_venues.sql`. The capacities come from koteng.no. The equipment and prices are placeholders until Kowork confirms them. The hero photo in `frontend/public/venues/kowork.webp` and the meeting room photo in `frontend/public/rooms/kowork-meeting-room.webp` are Kowork's own, from koteng.no. Brighten has a meeting room and a phone pod, seeded in `backend/app/migrations/003_brighten.sql`. brighten.no names both but lists no capacities, equipment, or prices, so all of those are placeholders until Brighten confirms them. The hero photo in `frontend/public/venues/brighten.webp` and the meeting room photo in `frontend/public/rooms/brighten-meeting-room.webp` are Brighten's own, from brighten.no. The site has no photo of the phone pod. Run its demo with `MARKETPLACE_VENUE=brighten`.

Add a venue by adding it to `backend/app/venues.py` and seeding its rooms in a new migration.

## Connect a device

Set `MARKETPLACE_DEVICE_TOKEN` to enable `POST /internal/device/events`. The device integration sends `Authorization: Bearer <token>`. For local testing, the fixture adapter accepts `type: room.released`, `event_id`, `external_room_id` (use `digs-demo-1` or `digs-demo-2` at Digs, `kowork-meeting-room` or `kowork-quiet-room` at Kowork, or `brighten-meeting-room` or `brighten-phone-pod` at Brighten), `block_id`, `released_at`, and `scheduled_end_at`. Send both timestamps as ISO 8601 strings with offsets, and reuse event and block IDs when retrying the same release.

When the real API is ready, set `MARKETPLACE_DEVICE_ADAPTER` to a trusted Python factory path such as `app.vendor_device:create_adapter`. The factory implements `DeviceAdapter` in `backend/app/device.py`. A webhook or a poller can pass the provider payload through the same adapter. The adapter supplies a source, stable IDs, and the release window. The backend handles deduplication, availability, quotes, and booking.
