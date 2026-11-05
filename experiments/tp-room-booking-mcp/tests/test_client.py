import json
import time
from pathlib import Path

import httpx
import pytest

from tp_room_booking_mcp.client import Settings, TPClient, TPError, time_window
from tp_room_booking_mcp.fixture import make_client
from tp_room_booking_mcp.login import save_cookies

START = "2026-12-01T12:00:00+01:00"
END = "2026-12-01T13:00:00+01:00"
ROOM = {"id": "R1", "size": 6, "available": True, "can_book": True}


def client_for(handler, tmp_path: Path, *, writes=True):
    return TPClient(
        Settings(backend="tp", state_file=tmp_path / "session.json", allow_writes=writes),
        httpx.MockTransport(handler),
    )


async def test_fixture_booking_lifecycle_and_overlap():
    c = make_client(Settings())
    try:
        assert (await c.session_status())["authenticated"]
        booked = await c.book("DEMO-G1", START, END, "Study", "")
        assert booked["booked"] is True
        assert len(await c.list_bookings()) == 1
        with pytest.raises(TPError, match="unavailable"):
            await c.book("DEMO-G1", START, END, "Duplicate", "")
        # Adjacent windows are valid, overlapping ones are not.
        await c.book("DEMO-G1", END, "2026-12-01T14:00:00+01:00", "Next", "")
        await c.cancel(booked["booking_id"])
        assert len(await c.list_bookings()) == 1
        assert (await c.search(START, END, ["DEMO-G1"]))[0]["available"]
    finally:
        await c.close()


async def test_live_payload_and_preflight_order(tmp_path):
    calls = []

    def handler(req):
        calls.append(req)
        if req.url.path.endswith("session.php"):
            return httpx.Response(200, json={"username": "test-user"})
        if req.url.path.endswith("possible.php"):
            assert req.url.params.get_list("roomid[]") == ["R1"]
            assert req.url.params["start"] == "2026-12-01T12:00:00"
            return httpx.Response(200, json=[ROOM])
        assert req.method == "POST"
        assert req.url.path == "/ntnu/ws/rombestilling/reservation.php"
        assert json.loads(req.content) == {
            "rooms": ["R1"],
            "userGroup": None,
            "name": "Study",
            "notes": "Note",
            "start": "2026-12-01T12:00:00",
            "end": "2026-12-01T13:00:00",
        }
        assert req.headers["origin"] == "https://tp.educloud.no"
        return httpx.Response(200, json={"reservations-completed": [{"ok": True, "id": "B1"}]})

    c = client_for(handler, tmp_path)
    try:
        assert (await c.book("R1", START, END, " Study ", "Note"))["booking_id"] == "B1"
        assert [req.method for req in calls] == ["GET", "GET", "POST"]
    finally:
        await c.close()


@pytest.mark.parametrize(
    "room",
    [
        {**ROOM, "available": False},
        {**ROOM, "can_book": False, "can_apply": True},
        {**ROOM, "place_booking": True},
        {**ROOM, "size": 0},
        {**ROOM, "id": "other"},
    ],
)
async def test_unbookable_rooms_never_trigger_write(tmp_path, room):
    def handler(req):
        assert req.method == "GET"
        return httpx.Response(
            200, json={"username": "test"} if req.url.path.endswith("session.php") else [room]
        )

    c = client_for(handler, tmp_path)
    try:
        with pytest.raises(TPError, match="unavailable"):
            await c.book("R1", START, END, "Test", "")
    finally:
        await c.close()


async def test_live_write_gate_makes_no_requests(tmp_path):
    def handler(req):
        pytest.fail("No HTTP requests expected when writes are disabled")

    c = client_for(handler, tmp_path, writes=False)
    try:
        with pytest.raises(TPError, match="disabled"):
            await c.book("R1", START, END, "Test", "")
        with pytest.raises(TPError, match="disabled"):
            await c.cancel("B1")
    finally:
        await c.close()


@pytest.mark.parametrize(
    "status,body", [(401, b"{}"), (403, b"{}"), (302, b""), (200, b"<html>Login</html>")]
)
async def test_auth_and_html_fail_cleanly(tmp_path, status, body):
    c = client_for(lambda _: httpx.Response(status, content=body), tmp_path)
    try:
        with pytest.raises(TPError, match="login|Login"):
            await c.search(START, END)
    finally:
        await c.close()


async def test_empty_session_is_not_authenticated(tmp_path):
    c = client_for(lambda _: httpx.Response(200, content=b""), tmp_path)
    try:
        assert not (await c.session_status())["authenticated"]
    finally:
        await c.close()


async def test_unknown_write_outcome_is_not_retried(tmp_path):
    writes = 0

    def handler(req):
        nonlocal writes
        if req.method == "POST":
            writes += 1
            raise httpx.ReadTimeout("secret-looking transport detail")
        return httpx.Response(
            200, json={"username": "test"} if req.url.path.endswith("session.php") else [ROOM]
        )

    c = client_for(handler, tmp_path)
    try:
        with pytest.raises(TPError, match="outcome is unknown"):
            await c.book("R1", START, END, "Test", "")
        assert writes == 1
    finally:
        await c.close()


@pytest.mark.parametrize(
    "status,body",
    [
        (500, b'{"error":"server failure"}'),
        (200, b""),
        (200, b"<html>proxy error</html>"),
    ],
)
async def test_uninterpretable_write_results_require_reconciliation(tmp_path, status, body):
    c = client_for(lambda _: httpx.Response(status, content=body), tmp_path)
    try:
        with pytest.raises(TPError, match="Check list_my_bookings"):
            await c.request("POST", "rombestilling/reservation.php", json={})
    finally:
        await c.close()


@pytest.mark.parametrize(
    "result",
    [
        {"reservations-completed": []},
        {"reservations-completed": [{"ok": False}]},
        {"reservations-completed": [{"ok": True}]},
        {"unexpected": True},
    ],
)
async def test_never_reports_booking_success_without_confirmed_id(tmp_path, result):
    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json=result)
        return httpx.Response(
            200, json={"username": "test"} if req.url.path.endswith("session.php") else [ROOM]
        )

    c = client_for(handler, tmp_path)
    try:
        with pytest.raises(TPError, match="Check list_my_bookings"):
            await c.book("R1", START, END, "Test", "")
    finally:
        await c.close()


async def test_cancellation_requires_own_booking_and_sends_id_query(tmp_path):
    deleted = []

    def handler(req):
        if req.method == "DELETE":
            deleted.append(req.url.params["id"])
            return httpx.Response(200, json={"deleted": True})
        return httpx.Response(
            200,
            json={"username": "test"} if req.url.path.endswith("session.php") else [{"id": "B1"}],
        )

    c = client_for(handler, tmp_path)
    try:
        with pytest.raises(TPError, match="own bookings"):
            await c.cancel("someone-elses-booking")
        assert deleted == []
        assert (await c.cancel("B1"))["cancelled"]
        assert deleted == ["B1"]
    finally:
        await c.close()


async def test_session_cookie_scoping_expiry_xsrf_and_revocation(tmp_path):
    path = tmp_path / "session.json"
    cookies = [
        {
            "name": "session",
            "value": "test-session",
            "domain": "tp.educloud.no",
            "path": "/ntnu/",
            "secure": True,
            "expires": time.time() + 3600,
        },
        {"name": "XSRF-TOKEN", "value": "abc%3D", "domain": "tp.educloud.no", "path": "/"},
        {
            "name": "expired",
            "value": "old",
            "domain": "tp.educloud.no",
            "path": "/",
            "expires": time.time() - 3600,
        },
        {"name": "wrong-path", "value": "no", "domain": "tp.educloud.no", "path": "/uio/"},
        {"name": "idp", "value": "no", "domain": "idp.feide.no", "path": "/"},
        {"name": "parent", "value": "ok", "domain": ".educloud.no", "path": "/"},
        {"name": "sibling", "value": "no", "domain": "other.educloud.no", "path": "/"},
    ]
    save_cookies(path, cookies)
    assert path.stat().st_mode & 0o777 == 0o600
    assert len(json.loads(path.read_text())["cookies"]) == 5
    requests = []

    def handler(req):
        requests.append(req)
        return httpx.Response(200, json={"username": "test"})

    c = client_for(handler, tmp_path)
    try:
        await c.session_status()
        cookie = requests[-1].headers["cookie"]
        assert "session=test-session" in cookie
        assert "parent=ok" in cookie and "sibling" not in cookie
        assert "expired" not in cookie and "wrong-path" not in cookie and "idp" not in cookie
        assert requests[-1].headers["X-XSRF-TOKEN"] == "abc="
        path.unlink()
        await c.session_status()
        assert "cookie" not in requests[-1].headers
    finally:
        await c.close()


@pytest.mark.parametrize(
    "start,end,expected",
    [
        (START, END, ("2026-12-01T12:00:00", "2026-12-01T13:00:00")),
        (
            "2026-12-01T11:00:00Z",
            "2026-12-01T12:00:00Z",
            ("2026-12-01T12:00:00", "2026-12-01T13:00:00"),
        ),
        (
            "2026-07-01T10:00:00Z",
            "2026-07-01T11:00:00Z",
            ("2026-07-01T12:00:00", "2026-07-01T13:00:00"),
        ),
    ],
)
def test_timezone_conversion(start, end, expected):
    assert time_window(start, end) == expected


@pytest.mark.parametrize(
    "start,end",
    [
        (END, START),
        (START, START),
        ("garbage", END),
        ("2026-12-01", END),
        ("2027-03-28T02:15:00", "2027-03-28T04:00:00"),
        ("2026-10-25T02:15:00", "2026-10-25T04:00:00"),
        ("2026-10-25T02:15:00+02:00", "2026-10-25T02:45:00+01:00"),
    ],
)
def test_invalid_or_ambiguous_windows(start, end):
    with pytest.raises(TPError):
        time_window(start, end)
