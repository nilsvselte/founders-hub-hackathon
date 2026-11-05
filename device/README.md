# device: room occupancy sensing

`device/` tells the marketplace whether a room is physically in use. Atech boards in each room send sensor readings over WiFi to the device server. The server works out occupancy and exposes it to the marketplace.

## Ownership

`device/` owns sensors, firmware, and occupancy: whether a room is occupied, since when, and whether the data can be trusted. It does not know what a booking is.

The marketplace owns bookings, no-show and overstay decisions, auto-release, and pricing. To detect a ghost booking, the marketplace compares its own booking with the occupancy data from `device/`.

| Folder | Owns |
| --- | --- |
| `firmware/` | Atech project (`project.yaml`) for the ESP32-S3 board. The board sends raw readings and stays simple. |
| `server/` | FastAPI app with SQLite, run with uv. Ingests telemetry, computes occupancy, serves the room API, and pushes events to the marketplace. |

## Hardware

Each board uses the following modules:

- **ToF sensor (VL53L5CX, 8×8):** the main presence signal. It measures 64 distances, and a person shows up as zones closer than the calibrated empty-room baseline. It is not a camera.
- **Temperature and humidity (AHT20):** context for the room view. The demo kit has no CO₂ sensor; `co2_ppm` stays in the contract for boards that have one.
- **Buttons:** the **Release room** button's RGB light shows room status: green for empty, red for occupied, and blue when the board cannot reach the server. The **Calibrate** button stores the empty-room baseline.

The demo board is a 14-port board: ToF on port 1, AHT20 on port 11, Release on port 13, and Calibrate on port 14.

The board sends readings about every 3 seconds. The server makes every decision, so changing thresholds does not need a reflash. WiFi is 2.4 GHz only. A phone hotspot works, and on an iPhone you must turn on **Maximize Compatibility**. The board and the device server's machine must be on the same network.

## API contract

All timestamps are ISO 8601 with a timezone offset. Room IDs are the marketplace's room IDs, such as `digs-demo-1`. The device server listens on port **8100**.

### 1. Board → device server (internal to `device/`)

`POST /v1/telemetry` with `Authorization: Bearer <device token>`

```json
{"device_id": "dev-1", "seq": 812, "uptime_ms": 2436000,
 "tof_mm": [1830, 1825, "... 64 values, row-major"],
 "co2_ppm": 640, "temp_c": 22.4, "rh_pct": 38.1,
 "buttons": {"release": 1, "calibrate": 0}}
```

`buttons` counts presses since the previous report. A press is also sent at once. The response is `{"ok": true, "room_id": "digs-demo-1", "occupied": true}`, and the board uses `occupied` for the LED.

Devices map to rooms in the server's `.env`, for example `DEVICES=dev-1:digs-demo-1`. A room can have several devices, and it counts as occupied when any of them sees someone.

`POST /v1/rooms/{room_id}/calibrate` stores the current ToF frame as the empty-room baseline. Run it once per room while the room is empty. Pressing the board's **Calibrate** button does the same thing.

### 2. Marketplace → device server (marketplace pulls)

`GET /v1/rooms` lists every room. `GET /v1/rooms/{room_id}` returns one room:

```json
{"room_id": "digs-demo-1", "occupied": false, "since": "2026-11-05T17:02:10+01:00",
 "online": true, "last_seen_at": "2026-11-05T17:12:03+01:00",
 "co2_ppm": 612, "temp_c": 22.4, "devices": ["dev-1"]}
```

`online` is false when no device for the room has reported in the last 30 seconds. `since` is when `occupied` last changed.

`GET /v1/rooms/{room_id}/presence?from=<ISO>&to=<ISO>` answers the no-show question: "was anyone in the room between these times?"

```json
{"room_id": "digs-demo-1", "from": "...", "to": "...",
 "any_presence": false, "occupied_seconds": 0,
 "first_seen_at": null, "last_seen_at": null, "coverage": 0.98}
```

`coverage` is the share of the window covered by device data, from 0 to 1. A room with low coverage was offline, so `any_presence: false` there does not prove a no-show.

### 3. Device server → marketplace (device pushes)

`POST {MARKETPLACE_URL}/internal/device/events` with `Authorization: Bearer <MARKETPLACE_DEVICE_TOKEN>`. This is the marketplace's existing endpoint.

The device server sends this event when a room's occupancy changes:

```json
{"type": "room.occupancy_changed", "event_id": "<uuid>", "external_room_id": "digs-demo-1",
 "occupied": false, "changed_at": "2026-11-05T17:02:10+01:00"}
```

It sends this event when staff press the release button:

```json
{"type": "room.release_requested", "event_id": "<uuid>", "external_room_id": "digs-demo-1",
 "requested_at": "2026-11-05T17:02:10+01:00"}
```

The device server cannot send `room.released`, because it does not know the booking's `block_id` or `scheduled_end_at`. The marketplace maps `room.release_requested` to the current block and decides whether to release it. Failed sends are retried with the same `event_id`, so the marketplace can deduplicate. The current `FixtureDeviceAdapter` returns `None` for these types, so the existing endpoint accepts them without breaking until the marketplace handles them.

## Run the device server

Use Python 3.12 or newer with uv. Run these from `device/server/`.

```sh
cp .env.example .env
uv sync
uv run --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

`--host 0.0.0.0` lets boards on the hotspot reach the server. Open `http://127.0.0.1:8100/` for a live room view, or `http://127.0.0.1:8100/docs` for the API docs. `GET /v1/outbox` shows the events sent to the marketplace and any send errors.

Set `DEVICES` to map each board to a room. Set `MARKETPLACE_URL` and `MARKETPLACE_DEVICE_TOKEN` to push events, and use the same token as the marketplace's `MARKETPLACE_DEVICE_TOKEN`. Leave `MARKETPLACE_URL` empty to queue events without sending them. Occupancy thresholds are in `.env.example`.

Run the tests with `uv run pytest`.

To calibrate a room, empty it, let the board report for a few seconds, and then run:

```sh
curl -X POST http://127.0.0.1:8100/v1/rooms/digs-demo-1/calibrate
```

## Flash the firmware

Install the Atech SDK with `uv tool install atech --with-executables-from platformio`. The PlatformIO part puts `pio` on the PATH, which `atech build` needs. Run these from `device/firmware/`.

```sh
cp secrets.example.h secrets.h   # then fill in the WiFi password and the server address
atech validate . && atech upload .
```

`secrets.h` is gitignored. `SERVER_URL` must use the device server machine's address on the hotspot, such as `http://172.20.10.3:8100/v1/telemetry`, and the server must run with `--host 0.0.0.0`. After flashing, the Release button turns blue while the board connects, then green or red once the server answers.
