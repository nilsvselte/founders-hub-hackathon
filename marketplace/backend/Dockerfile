FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /usr/local/bin/uv

WORKDIR /app/marketplace/backend
COPY experiments/tp-room-booking-mcp/pyproject.toml /app/experiments/tp-room-booking-mcp/pyproject.toml
COPY experiments/tp-room-booking-mcp/src /app/experiments/tp-room-booking-mcp/src
COPY marketplace/backend/pyproject.toml marketplace/backend/uv.lock ./
RUN uv sync --locked --no-dev

COPY marketplace/backend/app ./app

CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
