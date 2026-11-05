# standbyroom meeting room marketplace

Renters can browse venues, sign in, and choose **Book when available** to authorize standbyroom to book within their time window, group size, equipment needs, and total budget. The marketplace confirms a matching opening and reserves the slot in the same transaction. Hosts use a separate dashboard to publish rooms and release availability. Next.js serves the marketplace and FastAPI on Uvicorn manages accounts and bookings in PostgreSQL.

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

1. Set `MARKETPLACE_DEMO_MODE=1` in `backend/.env` before starting Uvicorn. Leave `ANTHROPIC_API_KEY` unset for the keyless demo.
2. Create a renter account, open a sample room, and choose **Book when available**. If the room has no eligible opening, press **Release demo room** to simulate an early release.
3. Show the confirmed reservation, final price, and booking reference. Choose **Add to Google Calendar** to open a prefilled event draft.

For live Claude matching, set `ANTHROPIC_API_KEY` in the backend environment. Pydantic AI uses Claude Sonnet 5.5 (`claude-sonnet-5-5`) by default. Override it with `ANTHROPIC_MODEL` or set `ANTHROPIC_WORKSPACE_ID` when your organization key requires a workspace. Keep these values in your local environment. Keyless demo mode uses a deterministic matcher and labels the result **Demo match**. Enable demo mode only against test inventory.

To test the host side, register as a host, create a listing, publish it, and release an opening from the host dashboard. Use a separate browser session to book it as a renter.

## Try the calendar assistant

Sign in as a renter and open **Calendar assistant** at `/agent` to create or revoke a local assistant token. Set room preferences and agent settings at `/account/preferences`. The [local MCP setup](agent/README.md) shows how to connect Claude and request suggestions. The assistant can search and suggest rooms without changing inventory. Review and approve the exact room, time, and price before it creates a hold and confirms a booking.

## Pilot venues

The public catalog shows published listings across venues. A room-specific standby request can only match an opening for that room. For the venue API and default room used by a demo release without an explicit room ID, set `MARKETPLACE_VENUE` to `digs` (Mesh at Digs, the default), `kowork` (Kowork at Kjøpmannsgata 40 in Trondheim), or `brighten` (Brighten at Bakke Bydelshus, Nordre Berggate 2).

To use Kowork as the default pilot in Docker Compose, run this from `marketplace/`.

```sh
MARKETPLACE_VENUE=kowork MARKETPLACE_DEMO_MODE=1 docker compose up --build -d --wait
```

The Kowork seed includes the shared meeting room, listed for groups of 8 to 12, and a quiet room. The capacity information comes from [Koteng](https://koteng.no/). The equipment and prices are sample values pending confirmation from Kowork. The catalog uses Kowork’s own meeting-room photo from [Koteng](https://koteng.no/). See [the venue migration](backend/app/migrations/002_venues.sql).

Brighten lists a meeting room and a phone pod. Their capacities, equipment, and prices are placeholders until Brighten confirms them. The catalog uses Brighten’s meeting-room photo from [Brighten](https://brighten.no/).

Mesh’s Digs listings use Mesh Community’s room photography for Driv and its shared Gnist and Spark gallery. Listings without a verified image are shown without a room photograph. [Mesh Community’s Trondheim room gallery](https://meshcommunity.com/trondheim/meeting-event)

Research for 26 additional Trondheim and Stjørdal venues is stored as listings. 14 of them are published: the five Scandic hotels, both Radisson Blu hotels, Rockheim, Salemhuset, Trondheim Spektrum, Banksalen, Olavshallen, Lager11, and OLO. Each has a photo of its own meeting or event space from its own website, and its listing was checked against that site. The other 12 stay unpublished until the customer roster confirms them. [Publish migration](backend/app/migrations/014_publish_venues_with_verified_space_photos.sql) Unpublishing these research listings preserves existing booking history. [Catalog research](backend/app/migrations/011_trondheim_venue_catalog.sql) · [Draft migration](backend/app/migrations/012_keep_unconfirmed_venue_leads_unpublished.sql)

Each of these venues has its own photo, labelled as a venue photo because the room names are generic. It shows a meeting room where the venue publishes one, and otherwise the hotel or building. The photos come from each venue's or hotel chain's own website. [Photo sources](backend/app/migrations/013_trondheim_venue_photos.sql)

## Run backend checks

From `marketplace/backend/`, run `uv run --locked python -m unittest discover -s tests -v`. Set `MARKETPLACE_TEST_DATABASE_URL` to a disposable PostgreSQL database to include the concurrent booking checks.

## Connect a device

1. Set the same `MARKETPLACE_DEVICE_TOKEN` in the marketplace API and [device server](../device/README.md). Point the device server's `MARKETPLACE_URL` to Uvicorn, such as `http://127.0.0.1:8000`, and set `DEVICES` to map each device ID to its marketplace room ID.
2. As a host, publish the room and use **Schedule a room block** to set the room's reserved start and end in Oslo time. The authenticated endpoint is `POST /host/rooms/{room_id}/blocks` with `starts_at` and `ends_at` as ISO 8601 timestamps with offsets.
3. Submit a renter request, then press **Release room** on the connected device while the block is active. The marketplace opens the remaining time after the turnaround buffer, which defaults to two minutes, and checks waiting requests. The device server's `/v1/outbox` shows delivery status.

The default `atech` adapter records `room.occupancy_changed` as the last reported physical state, which the host dashboard displays with its timestamp. `room.release_requested` opens the remainder of an active scheduled block once. For an isolated test, the legacy `room.released` fixture accepts `event_id`, `external_room_id`, `block_id`, `released_at`, and `scheduled_end_at`.

To use another provider, set `MARKETPLACE_DEVICE_ADAPTER` to a trusted Python factory path such as `app.vendor_device:create_adapter`. See the adapter interface in `backend/app/device.py`.
