"""SQLite storage and the occupancy state machine.

Only telemetry ingestion and calibration change room state. Reads never do, so
a device that goes offline freezes its room's state and reports online=false
instead of silently flipping the room to empty.

Timestamps are stored as Unix seconds (float, UTC).
"""

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Settings
from .occupancy import frame_present, valid_frame

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY,
    device_id TEXT NOT NULL,
    room_id TEXT NOT NULL,
    received_at REAL NOT NULL,
    seq INTEGER,
    uptime_ms INTEGER,
    present INTEGER,
    co2_ppm REAL,
    temp_c REAL,
    rh_pct REAL,
    tof_json TEXT
);
CREATE INDEX IF NOT EXISTS readings_room_time ON readings (room_id, received_at);

CREATE TABLE IF NOT EXISTS device_state (
    device_id TEXT PRIMARY KEY,
    room_id TEXT NOT NULL,
    last_seen_at REAL,
    last_present_at REAL,
    present_streak INTEGER NOT NULL DEFAULT 0,
    last_frame_json TEXT,
    baseline_json TEXT,
    co2_ppm REAL,
    temp_c REAL,
    rh_pct REAL
);

CREATE TABLE IF NOT EXISTS room_state (
    room_id TEXT PRIMARY KEY,
    occupied INTEGER NOT NULL,
    since REAL
);

CREATE TABLE IF NOT EXISTS room_changes (
    id INTEGER PRIMARY KEY,
    room_id TEXT NOT NULL,
    occupied INTEGER NOT NULL,
    changed_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS room_changes_room_time ON room_changes (room_id, changed_at);

CREATE TABLE IF NOT EXISTS outbox (
    event_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    next_attempt_at REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    sent_at REAL,
    last_error TEXT
);
CREATE INDEX IF NOT EXISTS outbox_due ON outbox (sent_at, next_attempt_at);
"""

# One reading is taken to cover this many seconds when computing coverage.
# Boards report about every 3 s, so a few missed reports still count as covered.
READING_COVERS_SECONDS = 10.0


class UnknownDevice(LookupError):
    pass


class UnknownRoom(LookupError):
    pass


class NothingToCalibrate(RuntimeError):
    pass


@dataclass
class TelemetryIn:
    device_id: str
    seq: int | None
    uptime_ms: int | None
    tof_mm: list | None
    co2_ppm: float | None
    temp_c: float | None
    rh_pct: float | None
    buttons: dict[str, int]


class Store:
    def __init__(self, settings: Settings, path: str | None = None):
        self.settings = settings
        db_path = path or settings.database_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)

    # ---- helpers -------------------------------------------------------

    def iso(self, ts: float | None) -> str | None:
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, self.settings.timezone).isoformat(timespec="seconds")

    def _enqueue(self, payload: dict, now: float) -> None:
        self._db.execute(
            "INSERT INTO outbox (event_id, payload_json, created_at, next_attempt_at) VALUES (?, ?, ?, ?)",
            (payload["event_id"], json.dumps(payload), now, now),
        )

    def _set_room(self, room_id: str, occupied: bool, at: float, now: float) -> None:
        self._db.execute(
            "INSERT INTO room_state (room_id, occupied, since) VALUES (?, ?, ?) "
            "ON CONFLICT(room_id) DO UPDATE SET occupied = excluded.occupied, since = excluded.since",
            (room_id, int(occupied), at),
        )
        self._db.execute(
            "INSERT INTO room_changes (room_id, occupied, changed_at) VALUES (?, ?, ?)",
            (room_id, int(occupied), at),
        )
        self._enqueue(
            {
                "type": "room.occupancy_changed",
                "event_id": str(uuid.uuid4()),
                "external_room_id": room_id,
                "occupied": occupied,
                "changed_at": self.iso(at),
            },
            now,
        )

    def _room_occupied(self, room_id: str) -> bool:
        row = self._db.execute("SELECT occupied FROM room_state WHERE room_id = ?", (room_id,)).fetchone()
        return bool(row and row["occupied"])

    def _evaluate_room(self, room_id: str, now: float) -> None:
        devices = self._db.execute(
            "SELECT present_streak, last_present_at FROM device_state WHERE room_id = ?", (room_id,)
        ).fetchall()
        present_now = any(d["present_streak"] >= self.settings.occupied_after_frames for d in devices)
        last_present = max((d["last_present_at"] for d in devices if d["last_present_at"]), default=None)
        occupied = self._room_occupied(room_id)
        if not occupied and present_now:
            self._set_room(room_id, True, now, now)
        elif occupied and (last_present is None or now - last_present >= self.settings.empty_after_seconds):
            # The room emptied when the last person was seen, not when the timeout ran out.
            self._set_room(room_id, False, last_present if last_present is not None else now, now)

    # ---- writes --------------------------------------------------------

    def ingest(self, t: TelemetryIn, now: float) -> tuple[str, bool]:
        room_id = self.settings.devices.get(t.device_id)
        if room_id is None:
            raise UnknownDevice(t.device_id)
        frame = valid_frame(t.tof_mm)

        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                state = self._db.execute(
                    "SELECT * FROM device_state WHERE device_id = ?", (t.device_id,)
                ).fetchone()
                baseline = json.loads(state["baseline_json"]) if state and state["baseline_json"] else None
                streak = state["present_streak"] if state else 0
                last_present_at = state["last_present_at"] if state else None

                present = None
                if frame is not None:
                    present = frame_present(frame, baseline, self.settings)
                    if present:
                        streak += 1
                        last_present_at = now
                    else:
                        streak = 0

                self._db.execute(
                    "INSERT INTO device_state (device_id, room_id, last_seen_at, last_present_at, present_streak, "
                    "last_frame_json, co2_ppm, temp_c, rh_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(device_id) DO UPDATE SET room_id = excluded.room_id, "
                    "last_seen_at = excluded.last_seen_at, last_present_at = excluded.last_present_at, "
                    "present_streak = excluded.present_streak, "
                    "last_frame_json = COALESCE(excluded.last_frame_json, device_state.last_frame_json), "
                    "co2_ppm = COALESCE(excluded.co2_ppm, device_state.co2_ppm), "
                    "temp_c = COALESCE(excluded.temp_c, device_state.temp_c), "
                    "rh_pct = COALESCE(excluded.rh_pct, device_state.rh_pct)",
                    (
                        t.device_id, room_id, now, last_present_at, streak,
                        json.dumps(frame) if frame is not None else None,
                        t.co2_ppm, t.temp_c, t.rh_pct,
                    ),
                )
                self._db.execute(
                    "INSERT INTO readings (device_id, room_id, received_at, seq, uptime_ms, present, co2_ppm, "
                    "temp_c, rh_pct, tof_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        t.device_id, room_id, now, t.seq, t.uptime_ms,
                        None if present is None else int(present),
                        t.co2_ppm, t.temp_c, t.rh_pct,
                        json.dumps(frame) if frame is not None else None,
                    ),
                )
                if frame is not None:
                    self._evaluate_room(room_id, now)

                if t.buttons.get("release", 0) > 0:
                    self._enqueue(
                        {
                            "type": "room.release_requested",
                            "event_id": str(uuid.uuid4()),
                            "external_room_id": room_id,
                            "requested_at": self.iso(now),
                        },
                        now,
                    )
                occupied = self._room_occupied(room_id)
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        return room_id, occupied

    def calibrate(self, room_id: str, now: float) -> list[str]:
        """Store each fresh device frame in the room as its empty-room baseline."""
        if room_id not in self.settings.rooms:
            raise UnknownRoom(room_id)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                rows = self._db.execute(
                    "SELECT device_id FROM device_state WHERE room_id = ? AND last_frame_json IS NOT NULL "
                    "AND last_seen_at >= ?",
                    (room_id, now - self.settings.offline_after_seconds),
                ).fetchall()
                if not rows:
                    raise NothingToCalibrate(room_id)
                self._db.execute(
                    "UPDATE device_state SET baseline_json = last_frame_json, present_streak = 0, "
                    "last_present_at = NULL WHERE room_id = ? AND last_frame_json IS NOT NULL AND last_seen_at >= ?",
                    (room_id, now - self.settings.offline_after_seconds),
                )
                if self._room_occupied(room_id):
                    self._set_room(room_id, False, now, now)
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        return [r["device_id"] for r in rows]

    # ---- reads ---------------------------------------------------------

    def room(self, room_id: str, now: float) -> dict:
        if room_id not in self.settings.rooms:
            raise UnknownRoom(room_id)
        with self._lock:
            state = self._db.execute("SELECT * FROM room_state WHERE room_id = ?", (room_id,)).fetchone()
            devices = self._db.execute(
                "SELECT * FROM device_state WHERE room_id = ? ORDER BY last_seen_at DESC", (room_id,)
            ).fetchall()
        last_seen = max((d["last_seen_at"] for d in devices if d["last_seen_at"]), default=None)
        latest = devices[0] if devices else None
        return {
            "room_id": room_id,
            "occupied": bool(state and state["occupied"]),
            "since": self.iso(state["since"]) if state else None,
            "online": last_seen is not None and now - last_seen < self.settings.offline_after_seconds,
            "last_seen_at": self.iso(last_seen),
            "co2_ppm": latest["co2_ppm"] if latest else None,
            "temp_c": latest["temp_c"] if latest else None,
            "devices": self.settings.devices_in(room_id),
        }

    def rooms(self, now: float) -> list[dict]:
        return [self.room(room_id, now) for room_id in self.settings.rooms]

    def presence(self, room_id: str, start: float, end: float, now: float) -> dict:
        """Was anyone in the room between start and end?"""
        if room_id not in self.settings.rooms:
            raise UnknownRoom(room_id)
        horizon = min(end, now)  # nothing is known about the future
        with self._lock:
            before = self._db.execute(
                "SELECT occupied FROM room_changes WHERE room_id = ? AND changed_at <= ? "
                "ORDER BY changed_at DESC, id DESC LIMIT 1",
                (room_id, start),
            ).fetchone()
            changes = self._db.execute(
                "SELECT occupied, changed_at FROM room_changes WHERE room_id = ? AND changed_at > ? "
                "AND changed_at < ? ORDER BY changed_at, id",
                (room_id, start, horizon),
            ).fetchall()
            times = [
                r["received_at"]
                for r in self._db.execute(
                    "SELECT received_at FROM readings WHERE room_id = ? AND received_at >= ? AND received_at < ? "
                    "ORDER BY received_at",
                    (room_id, start - READING_COVERS_SECONDS, horizon),
                )
            ]

        # Occupied intervals inside [start, horizon].
        intervals: list[tuple[float, float]] = []
        open_at = start if before and before["occupied"] else None
        for c in changes:
            if c["occupied"] and open_at is None:
                open_at = c["changed_at"]
            elif not c["occupied"] and open_at is not None:
                intervals.append((open_at, c["changed_at"]))
                open_at = None
        if open_at is not None and open_at < horizon:
            intervals.append((open_at, horizon))
        occupied_seconds = sum(b - a for a, b in intervals)

        # Share of [start, horizon] covered by readings.
        covered, cursor = 0.0, start
        for t in times:
            lo, hi = max(t, cursor), min(t + READING_COVERS_SECONDS, horizon)
            if hi > lo:
                covered += hi - lo
                cursor = hi
        span = end - start
        coverage = covered / span if span > 0 else 0.0

        return {
            "room_id": room_id,
            "from": self.iso(start),
            "to": self.iso(end),
            "any_presence": bool(intervals),
            "occupied_seconds": round(occupied_seconds),
            "first_seen_at": self.iso(intervals[0][0]) if intervals else None,
            "last_seen_at": self.iso(intervals[-1][1]) if intervals else None,
            "coverage": round(min(coverage, 1.0), 3),
        }

    # ---- outbox --------------------------------------------------------

    def due_events(self, now: float, limit: int = 20) -> list[tuple[str, dict, int]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT event_id, payload_json, attempts FROM outbox WHERE sent_at IS NULL "
                "AND next_attempt_at <= ? ORDER BY created_at LIMIT ?",
                (now, limit),
            ).fetchall()
        return [(r["event_id"], json.loads(r["payload_json"]), r["attempts"]) for r in rows]

    def mark_sent(self, event_id: str, now: float) -> None:
        with self._lock:
            self._db.execute("UPDATE outbox SET sent_at = ?, last_error = NULL WHERE event_id = ?", (now, event_id))

    def mark_failed(self, event_id: str, attempts: int, error: str, now: float) -> None:
        backoff = min(60.0, 2.0 ** attempts)
        with self._lock:
            self._db.execute(
                "UPDATE outbox SET attempts = ?, next_attempt_at = ?, last_error = ? WHERE event_id = ?",
                (attempts + 1, now + backoff, error[:500], event_id),
            )

    def outbox(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM outbox ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "event_id": r["event_id"],
                "payload": json.loads(r["payload_json"]),
                "created_at": self.iso(r["created_at"]),
                "sent_at": self.iso(r["sent_at"]),
                "attempts": r["attempts"],
                "last_error": r["last_error"],
            }
            for r in rows
        ]
