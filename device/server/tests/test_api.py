from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app
from app.store import Store

T0 = datetime(2026, 11, 5, 16, 0, tzinfo=timezone.utc).timestamp()
EMPTY = [2000] * 64
PERSON = [2000] * 60 + [900] * 4  # four zones much closer than the wall


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


@pytest.fixture
def env():
    settings = replace(
        load_settings(),
        devices={"dev-1": "digs-demo-1", "dev-2": "digs-demo-2"},
        device_token="",
        marketplace_url="",
        empty_after_seconds=30,
        occupied_after_frames=2,
    )
    store = Store(settings, ":memory:")
    app = create_app(store, start_push=False)
    clock = Clock()
    app.state.clock = clock
    return TestClient(app), store, clock


def send(client, clock, frame, device="dev-1", advance=3, **extra):
    clock.t += advance
    r = client.post("/v1/telemetry", json={"device_id": device, "tof_mm": frame, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def event_types(store):
    return [e["payload"]["type"] for e in reversed(store.outbox())]


def test_room_turns_occupied_then_empty(env):
    client, store, clock = env
    send(client, clock, EMPTY)
    client.post("/v1/rooms/digs-demo-1/calibrate").raise_for_status()

    assert send(client, clock, PERSON)["occupied"] is False  # one frame is not enough
    assert send(client, clock, PERSON)["occupied"] is True
    left_at = clock.t
    assert send(client, clock, EMPTY, advance=10)["occupied"] is True  # still within quiet period
    assert send(client, clock, EMPTY, advance=25)["occupied"] is False

    room = client.get("/v1/rooms/digs-demo-1").json()
    assert room["occupied"] is False and room["online"] is True
    assert room["since"] == datetime.fromtimestamp(left_at, store.settings.timezone).isoformat(timespec="seconds")

    changes = [e["payload"] for e in reversed(store.outbox()) if e["payload"]["type"] == "room.occupancy_changed"]
    assert [c["occupied"] for c in changes] == [True, False]
    assert all(c["external_room_id"] == "digs-demo-1" for c in changes)


def test_without_baseline_near_zones_count_as_presence(env):
    client, _, clock = env
    send(client, clock, PERSON)
    assert send(client, clock, PERSON)["occupied"] is True


def test_calibration_ignores_furniture(env):
    client, _, clock = env
    furniture = [2000] * 54 + [800] * 10  # a table close to the sensor
    send(client, clock, furniture)
    client.post("/v1/rooms/digs-demo-1/calibrate").raise_for_status()
    send(client, clock, furniture)
    assert send(client, clock, furniture)["occupied"] is False


def test_calibrate_needs_a_frame(env):
    client, _, _ = env
    assert client.post("/v1/rooms/digs-demo-1/calibrate").status_code == 409
    assert client.post("/v1/rooms/nope/calibrate").status_code == 404


def test_release_button_queues_event(env):
    client, store, clock = env
    send(client, clock, EMPTY, buttons={"release": 1})
    events = [e["payload"] for e in store.outbox()]
    assert events[0]["type"] == "room.release_requested"
    assert events[0]["external_room_id"] == "digs-demo-1"


def test_reading_without_tof_keeps_state(env):
    client, store, clock = env
    send(client, clock, PERSON)
    send(client, clock, PERSON)
    clock.t += 60
    r = client.post("/v1/telemetry", json={"device_id": "dev-1", "co2_ppm": 700})
    assert r.json()["occupied"] is True  # no ToF frame, no decision
    assert client.get("/v1/rooms/digs-demo-1").json()["co2_ppm"] == 700


def test_offline_freezes_state(env):
    client, _, clock = env
    send(client, clock, PERSON)
    send(client, clock, PERSON)
    clock.t += 120
    room = client.get("/v1/rooms/digs-demo-1").json()
    assert room["occupied"] is True and room["online"] is False


def test_unknown_device_rejected(env):
    client, _, _ = env
    r = client.post("/v1/telemetry", json={"device_id": "ghost", "tof_mm": EMPTY})
    assert r.status_code == 404


def test_bad_frame_length_rejected(env):
    client, _, _ = env
    r = client.post("/v1/telemetry", json={"device_id": "dev-1", "tof_mm": [1, 2, 3]})
    assert r.status_code == 422


def test_device_token(env):
    client, store, _ = env
    client.app.state.store = Store(replace(store.settings, device_token="s3cret"), ":memory:")
    assert client.post("/v1/telemetry", json={"device_id": "dev-1"}).status_code == 401
    ok = client.post("/v1/telemetry", json={"device_id": "dev-1"}, headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200


def test_presence_no_show(env):
    client, _, clock = env
    start = clock.t
    for _ in range(100):  # 5 minutes of empty frames
        send(client, clock, EMPTY)
    body = client.get(
        "/v1/rooms/digs-demo-1/presence", params={"from": iso(start), "to": iso(clock.t)}
    ).json()
    assert body["any_presence"] is False
    assert body["occupied_seconds"] == 0
    assert body["coverage"] > 0.95


def test_presence_someone_showed_up(env):
    client, _, clock = env
    start = clock.t
    for _ in range(10):
        send(client, clock, EMPTY)
    for _ in range(20):
        send(client, clock, PERSON)
    for _ in range(20):
        send(client, clock, EMPTY)
    body = client.get(
        "/v1/rooms/digs-demo-1/presence", params={"from": iso(start), "to": iso(clock.t)}
    ).json()
    assert body["any_presence"] is True
    assert 50 <= body["occupied_seconds"] <= 65
    assert body["first_seen_at"] and body["last_seen_at"]


def test_presence_offline_has_low_coverage(env):
    client, _, clock = env
    start = clock.t
    clock.t += 600
    body = client.get(
        "/v1/rooms/digs-demo-1/presence", params={"from": iso(start), "to": iso(clock.t)}
    ).json()
    assert body["any_presence"] is False and body["coverage"] == 0


def test_presence_open_interval_runs_to_now(env):
    client, _, clock = env
    start = clock.t
    send(client, clock, PERSON)
    send(client, clock, PERSON)
    for _ in range(5):
        send(client, clock, PERSON)
    body = client.get(
        "/v1/rooms/digs-demo-1/presence", params={"from": iso(start), "to": iso(clock.t + 3600)}
    ).json()
    assert body["any_presence"] is True
    assert body["occupied_seconds"] == 15


def test_presence_validates_window(env):
    client, _, clock = env
    params = {"from": iso(clock.t), "to": iso(clock.t - 10)}
    assert client.get("/v1/rooms/digs-demo-1/presence", params=params).status_code == 422
    naive = {"from": "2026-11-05T10:00:00", "to": "2026-11-05T11:00:00"}
    assert client.get("/v1/rooms/digs-demo-1/presence", params=naive).status_code == 422


def test_rooms_lists_configured_rooms(env):
    client, _, _ = env
    rooms = client.get("/v1/rooms").json()
    assert [r["room_id"] for r in rooms] == ["digs-demo-1", "digs-demo-2"]
    assert all(r["online"] is False for r in rooms)


def test_two_devices_one_room(env):
    client, store, clock = env
    store.settings.devices["dev-2"] = "digs-demo-1"
    send(client, clock, EMPTY, device="dev-1")
    send(client, clock, PERSON, device="dev-2", advance=0)
    send(client, clock, EMPTY, device="dev-1")
    assert send(client, clock, PERSON, device="dev-2", advance=0)["occupied"] is True


def test_calibrate_button(env):
    client, _, clock = env
    furniture = [2000] * 54 + [800] * 10
    send(client, clock, furniture)
    assert send(client, clock, furniture)["occupied"] is True  # uncalibrated: table looks like a person
    assert send(client, clock, furniture, buttons={"calibrate": 1})["occupied"] is False
    send(client, clock, furniture)
    assert send(client, clock, furniture)["occupied"] is False


def test_out_of_range_zones_are_ignored(env):
    client, _, clock = env
    send(client, clock, [32767] * 64)
    client.post("/v1/rooms/digs-demo-1/calibrate").raise_for_status()
    flicker = [3900] * 64  # far wall flickering in and out of range
    send(client, clock, flicker)
    assert send(client, clock, flicker)["occupied"] is False
    send(client, clock, [32767] * 60 + [900] * 4)
    assert send(client, clock, [32767] * 60 + [900] * 4)["occupied"] is True
