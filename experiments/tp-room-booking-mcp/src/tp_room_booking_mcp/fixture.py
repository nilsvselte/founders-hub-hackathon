"""Synthetic TP HTTP service for experiments. Never makes network requests."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .client import Settings, TPClient


class FixtureService:
    def __init__(self, state_file: Path | None = None):
        self.state_file = state_file
        self.bookings: dict[str, dict] = {}
        self.counter = 0
        if state_file and state_file.exists():
            state = json.loads(state_file.read_text())
            self.bookings = state["bookings"]
            self.counter = state["counter"]
        self.rooms = [
            {
                "id": "DEMO-G1",
                "name": "Demo Gløshaugen 1",
                "size": 6,
                "area_id": "DEMO-GLOS",
                "area_name": "Demo Gløshaugen",
                "building_id": "DEMO-B1",
                "building_name": "Demo Realfagbygget",
                "available": True,
                "can_book": True,
                "place_booking": False,
                "roomtype": {"id": "GRUPPE", "name": "Grupperom"},
            },
            {
                "id": "DEMO-G2",
                "name": "Demo Gløshaugen 2",
                "size": 12,
                "area_id": "DEMO-GLOS",
                "area_name": "Demo Gløshaugen",
                "building_id": "DEMO-B1",
                "building_name": "Demo Realfagbygget",
                "available": True,
                "can_book": True,
                "place_booking": False,
                "roomtype": {"id": "GRUPPE", "name": "Grupperom"},
            },
        ]

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/user/session.php"):
            return httpx.Response(200, json={"username": "fixture-user"})
        if path.endswith("/room/2.0/areas.php"):
            return httpx.Response(
                200, json={"data": [{"id": "DEMO-GLOS", "name": "Demo Gløshaugen"}]}
            )
        if path.endswith("/room/2.0/buildings.php"):
            return httpx.Response(
                200,
                json={"data": [{"id": "DEMO-B1", "name": "Demo Realfagbygget", "areaid": "DEMO-GLOS"}]},
            )
        if path.endswith("/user/quotas.php"):
            return httpx.Response(200, json={"demo": True, "message": "Synthetic quota response"})
        if path.endswith("/rombestilling/bookings.php"):
            return httpx.Response(200, json=list(self.bookings.values()))
        if path.endswith("/rombestilling/possible.php"):
            start, end = request.url.params["start"], request.url.params["end"]
            ids = request.url.params.get_list("roomid[]")
            rooms = []
            for room in self.rooms:
                if ids and room["id"] not in ids:
                    continue
                available = not any(
                    booking["rooms"][0]["id"] == room["id"]
                    and booking["start"] < end
                    and start < booking["end"]
                    for booking in self.bookings.values()
                )
                rooms.append({**room, "available": available})
            return httpx.Response(200, json=rooms)
        if path.endswith("/rombestilling/reservation.php"):
            if request.method == "POST":
                data = json.loads(request.content)
                room_id = data["rooms"][0]
                if any(
                    b["rooms"][0]["id"] == room_id
                    and b["start"] < data["end"]
                    and data["start"] < b["end"]
                    for b in self.bookings.values()
                ):
                    return httpx.Response(409, json={"error": "Room occupied"})
                self.counter += 1
                booking_id = f"DEMO-BOOKING-{self.counter}"
                self.bookings[booking_id] = {
                    "id": booking_id,
                    "name": data["name"],
                    "notes": data["notes"],
                    "owner": "fixture-user",
                    "rooms": [{"id": room_id}],
                    "start": data["start"],
                    "end": data["end"],
                }
                self.save()
                return httpx.Response(
                    200, json={"reservations-completed": [{"ok": True, "id": booking_id}]}
                )
            if request.method == "DELETE":
                removed = self.bookings.pop(request.url.params["id"], None)
                self.save()
                return httpx.Response(200, json={"deleted": removed is not None})
        return httpx.Response(404, json={"error": "Unknown fixture route"})

    def save(self):
        if self.state_file is None:
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(dir=self.state_file.parent)
        try:
            with os.fdopen(fd, "w") as output:
                json.dump({"bookings": self.bookings, "counter": self.counter}, output)
            os.replace(temporary, self.state_file)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def make_client(settings: Settings) -> TPClient:
    if settings.backend == "tp":
        return TPClient(settings)
    state_path = os.getenv("TP_FIXTURE_STATE")
    service = FixtureService(Path(state_path) if state_path else None)

    class FixtureClient(TPClient):
        def _load_session(self):
            # Fixture mode must never read a real user's session file.
            return

    return FixtureClient(
        Settings(backend="fixture", allow_writes=True), httpx.MockTransport(service.handle)
    )


def envelope(client: TPClient, data: Any) -> dict:
    return {"backend": client.settings.backend, "timezone": "Europe/Oslo", "data": data}
