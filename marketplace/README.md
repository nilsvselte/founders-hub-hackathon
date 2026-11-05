# Mesh meeting room marketplace

The marketplace has a Next.js frontend and a FastAPI backend served by Uvicorn. The backend uses PostgreSQL. The starter page and health endpoints are ready for local development.

Use Node.js 22 or newer with pnpm 11, Python 3.12 or newer with uv, and Docker Compose for the local database.

## Start PostgreSQL

From `marketplace/`:

```sh
docker compose up -d --wait db
```

PostgreSQL listens on `127.0.0.1:5432` and stores data in a named volume. If you already have a PostgreSQL server, use its connection URL in the next step and skip Compose.

## Start the API

From `marketplace/backend/`:

```sh
cp .env.example .env
uv sync --locked
uv run --locked --env-file .env uvicorn app.main:app --reload
```

The API serves OpenAPI docs at `http://127.0.0.1:8000/docs`. `GET /health` checks the process. `GET /ready` runs a PostgreSQL query and returns HTTP 503 if the database is unavailable.

## Start the frontend

From `marketplace/frontend/`:

```sh
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000`. Next.js forwards `/api/*` to Uvicorn so browser requests use the same origin. Run `curl -f http://localhost:3000/api/ready` to check the connection through the frontend. To use a different API address, copy `.env.example` to `.env.local` in the frontend and set `MARKETPLACE_API_URL` before starting or building Next.js.
