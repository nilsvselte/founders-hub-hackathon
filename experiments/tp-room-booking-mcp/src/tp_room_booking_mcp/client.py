"""HTTP contract observed in TP's current frontend, not its older API-key API."""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from http.cookiejar import Cookie
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import httpx

ORIGIN = "https://tp.educloud.no"
BASE = f"{ORIGIN}/ntnu"
OSLO = ZoneInfo("Europe/Oslo")
TP_COOKIE_DOMAINS = {"tp.educloud.no", "educloud.no"}


class TPError(ValueError):
    """An actionable error safe to return through MCP."""


@dataclass(frozen=True)
class Settings:
    backend: str = "fixture"
    state_file: Path = Path(".state/session.json")
    allow_writes: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        backend = os.getenv("TP_BACKEND", "fixture")
        if backend not in {"fixture", "tp"}:
            raise TPError("TP_BACKEND must be 'fixture' or 'tp'.")
        return cls(
            backend=backend,
            state_file=Path(os.getenv("TP_STATE_FILE", ".state/session.json"))
            .expanduser()
            .resolve(),
            allow_writes=os.getenv("TP_ALLOW_WRITES") == "1",
        )


def time_window(start: str, end: str) -> tuple[str, str]:
    """Accept ISO times, convert offsets to Oslo and reject ambiguous local DST times."""
    parsed = []
    for value in (start, end):
        try:
            if "T" not in value:
                raise ValueError
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                first = dt.replace(tzinfo=OSLO, fold=0)
                second = dt.replace(tzinfo=OSLO, fold=1)
                if first.utcoffset() != second.utcoffset():
                    raise TPError(
                        "Ambiguous or nonexistent Oslo time; include an explicit UTC offset."
                    )
                dt = first
            dt = dt.astimezone(OSLO)
            if dt.microsecond:
                raise TPError("Use whole seconds for TP timestamps.")
            parsed.append(dt)
        except (ValueError, TypeError) as exc:
            if isinstance(exc, TPError):
                raise
            raise TPError("Use ISO timestamps, e.g. 2026-11-06T12:00:00+01:00.") from None
    a, b = parsed
    if b.timestamp() <= a.timestamp():
        raise TPError("end must be after start.")
    # The current TP frontend sends Oslo wall-clock values without an offset.
    # Its wire format cannot distinguish the two occurrences of a repeated DST hour.
    for dt in parsed:
        wall = dt.replace(tzinfo=None)
        if (
            wall.replace(tzinfo=OSLO, fold=0).utcoffset()
            != wall.replace(tzinfo=OSLO, fold=1).utcoffset()
        ):
            raise TPError(
                "TP's frontend timestamp format cannot represent this DST transition hour."
            )
    return a.strftime("%Y-%m-%dT%H:%M:%S"), b.strftime("%Y-%m-%dT%H:%M:%S")


def rows(data: Any) -> list[dict]:
    if isinstance(data, list) and all(isinstance(row, dict) for row in data):
        return data
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return rows(data["data"])
    raise TPError("Unexpected TP response shape; the upstream contract may have changed.")


def bookable(room: dict) -> bool:
    return (
        room.get("available") is True
        and room.get("can_book") is True
        and isinstance(room.get("size"), (int, float))
        and room["size"] > 0
        and not room.get("place_booking")
    )


class TPClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.http = httpx.AsyncClient(
            base_url=BASE + "/",
            timeout=20,
            follow_redirects=False,
            transport=transport,
            headers={
                "Accept": "application/json",
                "Origin": ORIGIN,
                "Referer": BASE + "/app/rombestilling/",
            },
        )
        self._state_mtime: int | None = None
        self._write_lock = asyncio.Lock()

    async def close(self):
        await self.http.aclose()

    def _load_session(self):
        path = self.settings.state_file
        if not path.exists():
            # Never continue with stale in-memory credentials after the state file is removed.
            self.http.cookies.clear()
            self._state_mtime = None
            return
        try:
            mtime = path.stat().st_mtime_ns
            if mtime == self._state_mtime:
                return
            state = json.loads(path.read_text())
            cookies = state["cookies"]
            if not isinstance(cookies, list):
                raise ValueError
            jar = httpx.Cookies()
            for item in cookies:
                domain = item["domain"]
                if domain.lstrip(".") not in TP_COOKIE_DOMAINS:
                    continue
                expiry = item.get("expires", -1)
                jar.jar.set_cookie(
                    Cookie(
                        version=0,
                        name=item["name"],
                        value=item["value"],
                        port=None,
                        port_specified=False,
                        domain=domain,
                        domain_specified=True,
                        domain_initial_dot=domain.startswith("."),
                        path=item.get("path", "/"),
                        path_specified=True,
                        secure=item.get("secure", True),
                        expires=int(expiry) if expiry > 0 else None,
                        discard=expiry <= 0,
                        comment=None,
                        comment_url=None,
                        rest={},
                    )
                )
            self.http.cookies = jar
            self._state_mtime = mtime
        except (OSError, ValueError, KeyError, TypeError):
            self.http.cookies.clear()
            raise TPError("Invalid session file. Run tp-room-booking-login again.") from None

    async def request(self, method: str, path: str, **kwargs) -> Any:
        self._load_session()
        req = self.http.build_request(method, "ws/" + path, **kwargs)
        # Match Axios's default same-origin XSRF behavior, if TP sets this cookie.
        cookies = SimpleCookie()
        cookies.load(req.headers.get("cookie", ""))
        if "XSRF-TOKEN" in cookies:
            req.headers["X-XSRF-TOKEN"] = unquote(cookies["XSRF-TOKEN"].value)
        try:
            response = await self.http.send(req)
        except httpx.TransportError:
            if method != "GET":
                raise TPError(
                    "TP write outcome is unknown. Check list_my_bookings before retrying."
                ) from None
            raise TPError("Cannot reach TP. Check your network and try again.") from None
        if response.status_code in {301, 302, 303, 307, 308, 401, 403}:
            raise TPError("TP requires login or denied access. Run tp-room-booking-login.")
        if not response.is_success:
            if method != "GET" and response.status_code >= 500:
                raise TPError(
                    f"TP returned HTTP {response.status_code}; write outcome is unknown. "
                    "Check list_my_bookings before retrying."
                )
            raise TPError(f"TP returned HTTP {response.status_code}. No automatic retry was made.")
        if not response.content.strip():
            if path in {"user/session.php", "user/quotas.php"}:
                return None
            if method != "GET":
                raise TPError("Empty write response. Check list_my_bookings before retrying.")
            raise TPError("TP returned an empty response. Check login and upstream compatibility.")
        try:
            data = response.json()
        except ValueError:
            if method != "GET":
                raise TPError(
                    "Non-JSON write response. Check list_my_bookings before retrying."
                ) from None
            raise TPError(
                "TP returned non-JSON content. Check login and upstream compatibility."
            ) from None
        if isinstance(data, dict) and data.get("error"):
            raise TPError("TP rejected this request. Check permissions and booking limits in TP.")
        return data

    async def session_status(self) -> dict:
        session = await self.request("GET", "user/session.php")
        return {
            "authenticated": bool(isinstance(session, dict) and session.get("username")),
            "username": session.get("username") if isinstance(session, dict) else None,
            "writes_enabled": self.settings.allow_writes,
        }

    async def require_login(self):
        if not (await self.session_status())["authenticated"]:
            raise TPError("Sign in first with tp-room-booking-login.")

    async def list_locations(self) -> dict:
        areas = rows(await self.request("GET", "room/2.0/areas.php"))
        buildings = rows(await self.request("GET", "room/2.0/buildings.php"))
        return {"areas": areas, "buildings": buildings}

    async def search(self, start: str, end: str, room_ids: list[str] | None = None) -> list[dict]:
        start, end = time_window(start, end)
        params = [("start", start), ("end", end)]
        params.extend(("roomid[]", room_id) for room_id in room_ids or [])
        return rows(await self.request("GET", "rombestilling/possible.php", params=params))

    async def list_bookings(self) -> list[dict]:
        return rows(await self.request("GET", "rombestilling/bookings.php"))

    async def quotas(self) -> Any:
        await self.require_login()
        return await self.request("GET", "user/quotas.php")

    def require_writes(self):
        if not self.settings.allow_writes:
            raise TPError(
                "Live writes are disabled. Set TP_ALLOW_WRITES=1 to enable booking/cancellation."
            )

    async def book(self, room_id: str, start: str, end: str, name: str, notes: str) -> dict:
        self.require_writes()
        start, end = time_window(start, end)
        if not name.strip():
            raise TPError("Booking name cannot be empty.")
        async with self._write_lock:
            await self.require_login()
            available = await self.search(start, end, [room_id])
            if not any(str(room.get("id")) == room_id and bookable(room) for room in available):
                raise TPError("Room is unavailable or not directly bookable by this user.")
            payload = {
                "rooms": [room_id],
                "userGroup": None,
                "name": name.strip(),
                "notes": notes,
                "start": start,
                "end": end,
            }
            data = await self.request("POST", "rombestilling/reservation.php", json=payload)
            completed = data.get("reservations-completed") if isinstance(data, dict) else None
            if not isinstance(completed, list) or len(completed) != 1:
                raise TPError("Unexpected booking result. Check list_my_bookings before retrying.")
            result = completed[0]
            if not isinstance(result, dict) or result.get("ok") is not True or not result.get("id"):
                raise TPError(
                    "TP did not confirm a booking. Check list_my_bookings before retrying."
                )
            return {
                "booked": True,
                "booking_id": str(result["id"]),
                "room_id": room_id,
                "start": start,
                "end": end,
                "name": name.strip(),
                "upstream": data,
            }

    async def cancel(self, booking_id: str) -> dict:
        self.require_writes()
        async with self._write_lock:
            await self.require_login()
            # Restrict cancellation to IDs returned by the current user's own-bookings endpoint.
            bookings = await self.list_bookings()
            if not any(str(row.get("id")) == booking_id for row in bookings):
                raise TPError("Booking ID was not found in your own bookings.")
            data = await self.request(
                "DELETE", "rombestilling/reservation.php", params={"id": booking_id}
            )
            if not isinstance(data, dict) or data.get("deleted") is not True:
                raise TPError("TP did not confirm cancellation. Check list_my_bookings.")
            return {"cancelled": True, "booking_id": booking_id}
