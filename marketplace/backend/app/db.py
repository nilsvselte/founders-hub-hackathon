import os
from datetime import UTC, date, datetime, time, timedelta
from itertools import islice
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from .pricing import PriceQuote, quote_price
from .venues import VENUES


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


_MIGRATION_DIR = Path(__file__).with_name("migrations")
_MIGRATION_LOCK = 982347119
_MAX_CANDIDATES = 12
_OSLO = ZoneInfo("Europe/Oslo")
_ROOM_COLUMNS = "id, name, city, venue_name AS venue, kind, description, image_key, capacity, equipment, hourly_rate_ore"
_OPENING_COLUMNS = """
    o.id AS opening_id, o.room_id, r.venue, o.start_at AS opening_start, o.end_at AS opening_end,
    CASE WHEN r.owner_id IS NULL THEN r.venue END AS catalog_venue_id,
    r.name AS room_name, r.venue_name AS room_venue, r.city AS room_city, r.kind AS room_kind,
    r.capacity, r.equipment, r.published,
    r.hourly_rate_ore, r.minimum_hourly_rate_ore, r.maximum_hourly_rate_ore
"""


def _connect():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("Database connection is not configured")
    connection = psycopg.connect(dsn, connect_timeout=3, row_factory=dict_row)
    try:
        _migrate(connection)
        return connection
    except Exception:
        connection.close()
        raise


def _migrate(connection):
    migrations = sorted(_MIGRATION_DIR.glob("*.sql"))
    with connection.transaction():
        present = connection.execute(
            "SELECT to_regclass('marketplace_migrations') IS NOT NULL AS present"
        ).fetchone()["present"]
        if present:
            applied = {row["name"] for row in connection.execute("SELECT name FROM marketplace_migrations")}
            if all(path.name in applied for path in migrations):
                return

        connection.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK,))
        connection.execute("CREATE TABLE IF NOT EXISTS marketplace_migrations (name text PRIMARY KEY)")
        applied = {row["name"] for row in connection.execute("SELECT name FROM marketplace_migrations")}
        for path in migrations:
            if path.name not in applied:
                connection.execute(path.read_text(encoding="utf-8"), prepare=False)
                connection.execute("INSERT INTO marketplace_migrations VALUES (%s)", (path.name,))


def _datetime(value):
    timestamp = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if timestamp.utcoffset() is None:
        raise ValueError("Timestamps must include a timezone offset")
    return timestamp.astimezone(UTC)


def _json(row):
    data = {}
    for name, value in row.items():
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, UUID):
            value = str(value)
        data[name] = value
    return data


def _equipment(values):
    return sorted({value.strip().casefold().replace("-", " ").replace("_", " ") for value in values})


def check_ready() -> None:
    with _connect() as connection:
        connection.execute("SELECT 1")


def list_rooms() -> list[dict]:
    with _connect() as connection:
        return connection.execute(
            f"""
            SELECT {_ROOM_COLUMNS} FROM marketplace_rooms
            WHERE published AND city IS NOT NULL
            ORDER BY id
            """
        ).fetchall()


def get_room(room_id: str) -> dict | None:
    with _connect() as connection:
        return connection.execute(
            f"""
            SELECT {_ROOM_COLUMNS}, minimum_hourly_rate_ore, maximum_hourly_rate_ore
            FROM marketplace_rooms
            WHERE id = %s AND published AND city IS NOT NULL
            """,
            (room_id,),
        ).fetchone()


def get_room_quote(room_id: str, start_at: datetime, duration_minutes: int, now: datetime) -> PriceQuote | None:
    room = get_room(room_id)
    if room is None:
        return None
    return _quote(room, duration_minutes, start_at, now)


def create_request(data: dict, user_id: UUID) -> str:
    request_id = uuid4()
    with _connect() as connection:
        room_id = data["room_id"]
        venue_id = None
        if room_id is not None:
            room = connection.execute(
                "SELECT venue FROM marketplace_rooms WHERE id = %s AND published AND city IS NOT NULL FOR KEY SHARE",
                (room_id,),
            ).fetchone()
            if room is None:
                raise NotFound("Room not found")
            venue_id = room["venue"]
        connection.execute(
            """
            INSERT INTO marketplace_requests
                (id, earliest_start, latest_end, duration_minutes, party_size, equipment,
                 max_price_ore, preferences, user_id, room_id, venue, auto_confirm)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                request_id,
                _datetime(data["earliest_start"]),
                _datetime(data["latest_end"]),
                data["duration_minutes"],
                data["party_size"],
                _equipment(data["equipment"]),
                data["max_price_ore"],
                data["preferences"],
                user_id,
                room_id,
                venue_id,
                data.get("auto_confirm", False),
            ),
        )
    return str(request_id)


def _request(connection, request_id, *, user_id=None, lock=False):
    query = """
        SELECT request.*, room.name AS room_name
        FROM marketplace_requests request
        LEFT JOIN marketplace_rooms room ON room.id = request.room_id
        WHERE request.id = %s
    """
    parameters = (request_id,)
    if user_id is not None:
        query += " AND request.user_id = %s"
        parameters += (user_id,)
    if lock:
        query += " FOR UPDATE OF request"
    return connection.execute(query, parameters).fetchone()


def _active_offer(connection, request_id, now):
    return connection.execute(
        """
        SELECT o.*, r.name AS room_name, r.photo AS room_photo,
            r.venue_name AS room_venue, r.city AS room_city
        FROM marketplace_offers o
        JOIN marketplace_rooms r ON r.id = o.room_id
        WHERE o.request_id = %s AND (o.confirmed_at IS NOT NULL OR (r.published AND o.expires_at > %s))
        ORDER BY o.confirmed_at DESC NULLS LAST, o.created_at DESC
        LIMIT 1
        """,
        (request_id, now),
    ).fetchone()


def _status(connection, request, now):
    data = _json({key: value for key, value in request.items() if key != "user_id"})
    data.update(status="waiting", offer=None, booking_reference=None)
    offer = _active_offer(connection, request["id"], now)
    if offer:
        data["status"] = "confirmed" if offer["confirmed_at"] else "offered"
        data["offer"] = _json({
            key: offer[key]
            for key in ("id", "room_name", "room_photo", "room_venue", "room_city", "start_at", "end_at", "price_ore",
                        "expires_at", "match_reason", "match_provider", "booking_reference")
        })
        data["booking_reference"] = offer["booking_reference"]
    elif max(now, _datetime(request["earliest_start"])) + timedelta(minutes=request["duration_minutes"]) > request["latest_end"]:
        data["status"] = "expired"
    return data


def get_request(request_id: str, *, user_id: UUID | None = None) -> dict | None:
    with _connect() as connection:
        request = _request(connection, request_id, user_id=user_id)
        return _status(connection, request, datetime.now(UTC)) if request else None


def list_requests(user_id: UUID) -> list[dict]:
    with _connect() as connection:
        requests = connection.execute(
            """
            SELECT request.*, room.name AS room_name
            FROM marketplace_requests request
            LEFT JOIN marketplace_rooms room ON room.id = request.room_id
            WHERE request.user_id = %s
            ORDER BY request.created_at DESC, request.id DESC
            """,
            (user_id,),
        ).fetchall()
        now = datetime.now(UTC)
        return [_status(connection, request, now) for request in requests]


def list_pending_request_ids(room_id: str) -> list[str]:
    with _connect() as connection:
        return [
            str(row["id"])
            for row in connection.execute(
                """
                SELECT r.id
                FROM marketplace_requests r
                WHERE r.user_id IS NOT NULL
                  AND (r.room_id IS NULL OR r.room_id = %s)
                  AND r.latest_end >= GREATEST(r.earliest_start, now()) +
                      r.duration_minutes * interval '1 minute'
                  AND NOT EXISTS (
                      SELECT 1 FROM marketplace_offers o
                      JOIN marketplace_rooms room ON room.id = o.room_id
                      WHERE o.request_id = r.id
                        AND (o.confirmed_at IS NOT NULL OR (room.published AND o.expires_at > now()))
                  )
                ORDER BY r.created_at
                """,
                (room_id,),
            )
        ]


def _existing_opening(connection, event):
    return connection.execute(
        """
        SELECT id FROM marketplace_openings
        WHERE source = %s AND (event_id = %s OR (room_id = %s AND block_id = %s))
        ORDER BY event_id = %s DESC LIMIT 1
        """,
        (event["source"], event["event_id"], event["external_room_id"], event["block_id"], event["event_id"]),
    ).fetchone()


def record_release(event: dict) -> dict:
    with _connect() as connection:
        room = connection.execute(
            "SELECT id, published FROM marketplace_rooms WHERE id = %s FOR UPDATE",
            (event["external_room_id"],),
        ).fetchone()
        if not room:
            return {"created": False, "opening_id": None, "reason": "unknown_room"}
        if event["source"] == "host" and not room["published"]:
            return {"created": False, "opening_id": None, "reason": "room_unpublished"}
        return _record_release(connection, event, datetime.now(UTC))


def _valid_release_time(released_at, now):
    return now - timedelta(minutes=10) <= released_at <= now + timedelta(seconds=30)


def _record_release(connection, event, now):
    room_id = event["external_room_id"]
    previous = _existing_opening(connection, event)
    if previous:
        return {"created": False, "opening_id": str(previous["id"]), "reason": "duplicate_release"}

    released_at = _datetime(event["released_at"])
    end_at = _datetime(event["scheduled_end_at"])
    turnaround = int(os.getenv("MARKETPLACE_TURNAROUND_MINUTES", "2"))
    if turnaround < 0:
        raise RuntimeError("Turnaround cannot be negative")
    if not _valid_release_time(released_at, now):
        return {"created": False, "opening_id": None, "reason": "invalid_release_time"}
    start_at = max(released_at + timedelta(minutes=turnaround), now)
    if start_at >= end_at:
        return {"created": False, "opening_id": None, "reason": "no_remaining_time"}

    latest = connection.execute(
        """
        SELECT max(released_at) AS released_at FROM marketplace_openings
        WHERE room_id = %s AND source = %s
        """,
        (room_id, event["source"]),
    ).fetchone()["released_at"]
    if latest and released_at < latest:
        return {"created": False, "opening_id": None, "reason": "stale_release"}

    opening = connection.execute(
        """
        INSERT INTO marketplace_openings
            (id, room_id, source, event_id, block_id, released_at, start_at, end_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING RETURNING id
        """,
        (uuid4(), room_id, event["source"], event["event_id"], event["block_id"], released_at, start_at, end_at),
    ).fetchone()
    if opening:
        return {"created": True, "opening_id": str(opening["id"])}
    previous = _existing_opening(connection, event)
    return {
        "created": False,
        "opening_id": str(previous["id"]) if previous else None,
        "reason": "duplicate_release",
    }


def schedule_device_block(room_id: str, starts_at: datetime, ends_at: datetime, *, owner_id: UUID | None = None) -> dict:
    starts_at, ends_at = _datetime(starts_at), _datetime(ends_at)
    with _connect() as connection:
        room = connection.execute(
            """
            SELECT published, owner_id FROM marketplace_rooms WHERE id = %s FOR UPDATE
            """,
            (room_id,),
        ).fetchone()
        if not room or (owner_id is not None and owner_id != room["owner_id"]):
            raise NotFound("Listing not found")
        if not room["published"]:
            raise Conflict("Publish this listing before scheduling a device block")

        now = datetime.now(UTC)
        if starts_at >= ends_at or ends_at <= now:
            raise ValueError("The block must end after its start and in the future")
        blocks = connection.execute(
            """
            SELECT id, start_at, end_at FROM marketplace_device_blocks
            WHERE room_id = %s AND start_at < %s AND end_at > %s
            """,
            (room_id, ends_at, starts_at),
        ).fetchall()
        if blocks:
            block = blocks[0]
            if block["start_at"] == starts_at and block["end_at"] == ends_at:
                return _json(block)
            raise Conflict("The block overlaps another scheduled block")
        if _busy(connection, room_id, starts_at, ends_at, now):
            raise Conflict("The block overlaps a booking or a room hold")

        block = connection.execute(
            """
            INSERT INTO marketplace_device_blocks (id, room_id, start_at, end_at, created_at)
            VALUES (%s, %s, %s, %s, %s) RETURNING id, start_at, end_at
            """,
            (uuid4(), room_id, starts_at, ends_at, now),
        ).fetchone()
        return _json(block)


def _remember_device_event(connection, event, kind):
    return connection.execute(
        """
        INSERT INTO marketplace_device_events (source, event_id, room_id, kind)
        VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING event_id
        """,
        (event["source"], event["event_id"], event["external_room_id"], kind),
    ).fetchone() is not None


def record_occupancy(event: dict) -> dict:
    changed_at = _datetime(event["changed_at"])
    room_id = event["external_room_id"]
    with _connect() as connection:
        if not connection.execute(
            "SELECT 1 FROM marketplace_rooms WHERE id = %s FOR UPDATE", (room_id,),
        ).fetchone():
            return {"created": False, "reason": "unknown_room"}
        if not _remember_device_event(connection, event, "occupancy_changed"):
            return {"created": False, "reason": "duplicate_event"}
        if changed_at > datetime.now(UTC) + timedelta(seconds=30):
            return {"created": False, "reason": "invalid_occupancy_time"}
        updated = connection.execute(
            """
            INSERT INTO marketplace_room_occupancy (room_id, occupied, changed_at, source, event_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (room_id) DO UPDATE SET occupied = EXCLUDED.occupied,
                changed_at = EXCLUDED.changed_at, source = EXCLUDED.source, event_id = EXCLUDED.event_id
            WHERE EXCLUDED.changed_at > marketplace_room_occupancy.changed_at
            RETURNING room_id
            """,
            (room_id, event["occupied"], changed_at, event["source"], event["event_id"]),
        ).fetchone()
        return {"created": False, "reason": "occupancy_recorded" if updated else "stale_occupancy"}


def record_release_request(event: dict) -> dict:
    requested_at = _datetime(event["requested_at"])
    room_id = event["external_room_id"]
    with _connect() as connection:
        room = connection.execute(
            "SELECT published FROM marketplace_rooms WHERE id = %s FOR UPDATE", (room_id,),
        ).fetchone()
        if not room:
            return {"created": False, "reason": "unknown_room"}
        if not _remember_device_event(connection, event, "release_requested"):
            previous = connection.execute(
                """
                SELECT opening_id FROM marketplace_device_events
                WHERE source = %s AND event_id = %s AND room_id = %s AND kind = 'release_requested'
                """,
                (event["source"], event["event_id"], room_id),
            ).fetchone()
            opening_id = previous["opening_id"] if previous else None
            return {"created": False, "opening_id": str(opening_id) if opening_id else None, "reason": "duplicate_event"}
        if not room["published"]:
            return {"created": False, "reason": "room_unpublished"}

        now = datetime.now(UTC)
        if not _valid_release_time(requested_at, now):
            return {"created": False, "reason": "invalid_release_time"}
        block = connection.execute(
            """
            SELECT id, end_at, opening_id FROM marketplace_device_blocks
            WHERE room_id = %s AND start_at <= LEAST(%s, %s) AND end_at > GREATEST(%s, %s)
              AND created_at <= %s
            """,
            (room_id, requested_at, now, requested_at, now, requested_at),
        ).fetchone()
        if not block:
            return {"created": False, "reason": "no_active_block"}
        if block["opening_id"]:
            result = {"created": False, "opening_id": str(block["opening_id"]), "reason": "duplicate_release"}
        else:
            result = _record_release(connection, {
                **event,
                "block_id": str(block["id"]),
                "released_at": requested_at,
                "scheduled_end_at": block["end_at"],
            }, now)
            if result["created"]:
                connection.execute(
                    "UPDATE marketplace_device_blocks SET opening_id = %s WHERE id = %s",
                    (result["opening_id"], block["id"]),
                )
        if result.get("opening_id"):
            connection.execute(
                "UPDATE marketplace_device_events SET opening_id = %s WHERE source = %s AND event_id = %s",
                (result["opening_id"], event["source"], event["event_id"]),
            )
        return result


def _quote(room, minutes, start_at, now) -> PriceQuote:
    return quote_price(
        hourly_rate_ore=room["hourly_rate_ore"],
        minimum_hourly_rate_ore=room["minimum_hourly_rate_ore"],
        maximum_hourly_rate_ore=room["maximum_hourly_rate_ore"],
        start_at=start_at,
        duration_minutes=minutes,
        now=now,
    )


def _busy(connection, room_id, start_at, end_at, now, exclude=None):
    return connection.execute(
        """
        SELECT start_at, end_at FROM marketplace_offers
        WHERE room_id = %s AND start_at < %s AND end_at > %s
          AND (confirmed_at IS NOT NULL OR expires_at > %s)
          AND id IS DISTINCT FROM %s::uuid
        UNION ALL
        SELECT b.start_at, COALESCE(o.start_at, b.end_at) AS end_at
        FROM marketplace_device_blocks b
        LEFT JOIN marketplace_openings o ON o.id = b.opening_id
        WHERE b.room_id = %s AND b.start_at < %s AND COALESCE(o.start_at, b.end_at) > %s
        ORDER BY start_at
        """,
        (room_id, end_at, start_at, now, exclude, room_id, end_at, start_at),
    ).fetchall()


def _candidate(opening, request, start_at, end_at, now):
    if not opening["published"] or opening["room_city"] is None:
        return None
    if request["room_id"] is not None and opening["room_id"] != request["room_id"]:
        return None
    if request["venue"] is not None and opening["venue"] != request["venue"]:
        return None
    if opening["capacity"] < request["party_size"] or not set(request["equipment"]).issubset(opening["equipment"]):
        return None
    if start_at < max(_datetime(opening["opening_start"]), _datetime(request["earliest_start"]), now):
        return None
    if end_at > min(_datetime(opening["opening_end"]), _datetime(request["latest_end"])):
        return None
    if end_at - start_at != timedelta(minutes=request["duration_minutes"]):
        return None
    try:
        quote = _quote(opening, request["duration_minutes"], start_at, now)
    except OverflowError:
        return None
    if quote["price_ore"] > request["max_price_ore"]:
        return None
    return _json({
        **{key: opening[key] for key in (
            "opening_id", "room_id", "room_name", "room_venue", "room_city", "room_kind", "capacity", "equipment",
        )},
        "start_at": start_at,
        "end_at": end_at,
        "price_ore": quote["price_ore"],
        "venue_id": opening["catalog_venue_id"],
        "quote": quote,
    })


def _gaps(start_at, end_at, busy):
    cursor = start_at
    for block in busy:
        block_start = _datetime(block["start_at"])
        if cursor < block_start:
            yield cursor, block_start
        cursor = max(cursor, _datetime(block["end_at"]))
    if cursor < end_at:
        yield cursor, end_at


def _candidate_starts(gap_start, latest_start):
    if gap_start > latest_start:
        return
    yield gap_start
    try:
        first_day = gap_start.astimezone(_OSLO).date()
    except OverflowError:
        return

    # The base rate repeats weekly. Losing the last-minute discount cannot
    # make a later start cheaper, so the first week covers every cheaper band.
    for offset in range(min(7, (date.max - first_day).days) + 1):
        day = first_day + timedelta(days=offset)
        weekday = day.weekday()
        if weekday < 5:
            hours = (0, 9, 16) if weekday == 0 else (9, 16)
        else:
            hours = (0,) if weekday == 5 else ()
        for hour in hours:
            boundary = datetime.combine(day, time(hour), _OSLO).astimezone(UTC)
            if boundary > latest_start:
                return
            if boundary > gap_start:
                yield boundary


def list_candidates(request_id: str) -> list[dict]:
    with _connect() as connection:
        request = _request(connection, request_id)
        now = datetime.now(UTC)
        if not request or _active_offer(connection, request_id, now):
            return []
        return list(islice(_available_candidates(connection, request, now), _MAX_CANDIDATES))


def list_meeting_candidates(
    *,
    start_at: datetime,
    end_at: datetime,
    duration_minutes: int,
    party_size: int,
    equipment: list[str],
    max_price_ore: int,
    avoid_venues: list[str],
) -> list[dict]:
    request = {
        "room_id": None,
        "venue": None,
        "earliest_start": start_at,
        "latest_end": end_at,
        "duration_minutes": duration_minutes,
        "party_size": party_size,
        "equipment": equipment,
        "max_price_ore": max_price_ore,
    }
    with _connect() as connection:
        candidates = _available_candidates(connection, request, datetime.now(UTC), avoid_venues=avoid_venues)
        unique_rooms = {}
        for candidate in candidates:
            unique_rooms.setdefault(candidate["room_id"], candidate)
        return list(unique_rooms.values())


def _available_candidates(connection, request, now, *, avoid_venues=()):
    openings = connection.execute(
        f"""
        SELECT {_OPENING_COLUMNS}
        FROM marketplace_openings o
        JOIN marketplace_rooms r ON r.id = o.room_id
        WHERE o.end_at > GREATEST(%s, %s) AND o.start_at < %s
          AND r.published AND r.city IS NOT NULL AND r.capacity >= %s AND r.equipment @> %s::text[]
          AND o.room_id = COALESCE(%s, o.room_id)
          AND (%s::text IS NULL OR r.venue = %s)
          AND (r.owner_id IS NOT NULL OR r.venue IS NULL OR r.venue <> ALL(%s::text[]))
        ORDER BY o.start_at, o.id
        """,
        (
            now, request["earliest_start"], request["latest_end"], request["party_size"],
            request["equipment"], request["room_id"], request["venue"], request["venue"], list(avoid_venues),
        ),
    ).fetchall()
    duration = timedelta(minutes=request["duration_minutes"])
    earliest_start = _datetime(request["earliest_start"])
    latest_end = _datetime(request["latest_end"])
    for opening in openings:
        start_at = max(_datetime(opening["opening_start"]), earliest_start, now + timedelta(minutes=1))
        end_at = min(_datetime(opening["opening_end"]), latest_end)
        if end_at - start_at < duration:
            continue
        busy = _busy(connection, opening["room_id"], start_at, end_at, now)
        for gap_start, gap_end in _gaps(start_at, end_at, busy):
            for start in _candidate_starts(gap_start, gap_end - duration):
                candidate = _candidate(opening, request, start, start + duration, now)
                if candidate:
                    yield candidate
                    break


def _booking_reference(venue: str | None, offer_id: UUID) -> str:
    known_venue = VENUES.get(venue)
    prefix = known_venue.booking_prefix if known_venue else "ROOM"
    return f"{prefix}-{offer_id.hex[:12].upper()}"


def create_offer(request_id: str, candidate: dict, reason: str, provider: str) -> dict | None:
    start_at, end_at = _datetime(candidate["start_at"]), _datetime(candidate["end_at"])
    with _connect() as connection:
        request = _request(connection, request_id, lock=True)
        if not request:
            return None
        opening = connection.execute(
            f"""
            SELECT {_OPENING_COLUMNS}
            FROM marketplace_openings o
            JOIN marketplace_rooms r ON r.id = o.room_id
            WHERE o.id = %s
            FOR UPDATE OF r
            """,
            (candidate["opening_id"],),
        ).fetchone()
        now = datetime.now(UTC)
        if not opening or start_at <= now or _active_offer(connection, request_id, now):
            return None
        actual = _candidate(opening, request, start_at, end_at, now)
        if not actual or _busy(connection, opening["room_id"], start_at, end_at, now):
            return None

        offer_id = uuid4()
        confirmed_at = now if request["auto_confirm"] else None
        reference = _booking_reference(opening["venue"], offer_id) if confirmed_at else None
        offer = connection.execute(
            """
            INSERT INTO marketplace_offers
                (id, request_id, opening_id, room_id, start_at, end_at, price_ore, expires_at,
                 match_reason, match_provider, confirmed_at, booking_reference)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, start_at, end_at, price_ore, expires_at, match_reason, match_provider, booking_reference
            """,
            (offer_id, request_id, opening["opening_id"], opening["room_id"], start_at, end_at,
             actual["price_ore"], confirmed_at or min(now + timedelta(minutes=5), start_at),
             reason, provider, confirmed_at, reference),
        ).fetchone()
        return _json({**offer, "room_name": opening["room_name"]})


def accept_offer(request_id: str, offer_id: str, *, user_id: UUID) -> dict:
    with _connect() as connection:
        request = _request(connection, request_id, user_id=user_id, lock=True)
        if not request:
            raise NotFound("Standby request not found")
        room = connection.execute(
            """
            SELECT id FROM marketplace_rooms
            WHERE id = (SELECT room_id FROM marketplace_offers WHERE id = %s AND request_id = %s)
            FOR UPDATE
            """,
            (offer_id, request_id),
        ).fetchone()
        if not room:
            raise NotFound("Offer not found")
        # Take a fresh snapshot after the room lock. A host may have expired the
        # offer while this transaction was waiting for the room.
        offer = connection.execute(
            """
            SELECT o.*, w.start_at AS opening_start, w.end_at AS opening_end, r.published, r.venue
            FROM marketplace_offers o
            JOIN marketplace_openings w ON w.id = o.opening_id
            JOIN marketplace_rooms r ON r.id = o.room_id
            WHERE o.id = %s AND o.request_id = %s
            """,
            (offer_id, request_id),
        ).fetchone()
        if not offer:
            raise NotFound("Offer not found")
        now = datetime.now(UTC)
        if offer["confirmed_at"]:
            return _status(connection, request, now)
        if not offer["published"]:
            raise Conflict("The room is no longer available.")
        if offer["expires_at"] <= now:
            raise Conflict("This offer expired. Check your request for a new match.")
        start_at, end_at = _datetime(offer["start_at"]), _datetime(offer["end_at"])
        if not _datetime(offer["opening_start"]) <= start_at < end_at <= _datetime(offer["opening_end"]):
            raise Conflict("The room is no longer available at that time.")
        if _busy(connection, offer["room_id"], start_at, end_at, now, exclude=offer_id):
            raise Conflict("The room is no longer available at that time.")
        connection.execute(
            """
            UPDATE marketplace_offers SET confirmed_at = %s, booking_reference = %s
            WHERE id = %s
            """,
            (now, _booking_reference(offer["venue"], offer["id"]), offer_id),
        )
        return _status(connection, request, now)
