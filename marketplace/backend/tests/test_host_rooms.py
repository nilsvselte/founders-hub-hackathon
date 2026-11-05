import os
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import psycopg
from fastapi import Response
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app import db
from app.accounts import Account
from app.demo_host import claim_demo_rooms
from fastapi import HTTPException
from app.host import HostRoom, LiveRoom, list_host_rooms, live_room


@unittest.skipUnless(os.environ.get("MARKETPLACE_TEST_DATABASE_URL"), "requires disposable PostgreSQL")
class HostRoomStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        admin_dsn = os.environ["MARKETPLACE_TEST_DATABASE_URL"]
        schema_name = f"host_test_{uuid4().hex}"
        schema = sql.Identifier(schema_name)
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))

        def drop_schema():
            with psycopg.connect(admin_dsn, autocommit=True) as connection:
                connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))

        cls.addClassCleanup(drop_schema)
        dsn = make_conninfo(admin_dsn, options=f"-csearch_path={schema_name}")
        environment = patch.dict(os.environ, {"DATABASE_URL": dsn})
        environment.start()
        cls.addClassCleanup(environment.stop)
        db.check_ready()

    def setUp(self):
        self.host = Account(id=uuid4(), name="Host", email=f"{uuid4()}@example.test", role="host")
        self.room_id = f"host-test-{uuid4().hex}"
        with db._connect() as connection:
            connection.execute(
                """
                INSERT INTO marketplace_users (id, name, email, role, password_salt, password_hash)
                VALUES (%s, 'Host', %s, 'host', %s, %s)
                """,
                (self.host.id, self.host.email, bytes(16), bytes(32)),
            )
            connection.execute(
                """
                INSERT INTO marketplace_rooms (
                    id, owner_id, name, city, venue_name, kind, description, image_key, capacity, equipment,
                    hourly_rate_ore, minimum_hourly_rate_ore, maximum_hourly_rate_ore, published
                ) VALUES (%s, %s, 'Room', 'Trondheim', 'Venue', 'Meeting room', 'Test',
                          'none', 8, ARRAY['screen'], 20000, 10000, 40000, true)
                """,
                (self.room_id, self.host.id),
            )

    def rooms(self) -> list[HostRoom]:
        return [HostRoom.model_validate(row) for row in list_host_rooms(self.host, Response())]

    def book(self, start_at, end_at, reference):
        opening_id = uuid4()
        request_id = uuid4()
        with db._connect() as connection:
            connection.execute(
                """
                INSERT INTO marketplace_openings (id, room_id, source, event_id, block_id, released_at, start_at, end_at)
                VALUES (%s, %s, 'host', %s, %s, %s, %s, %s)
                """,
                (opening_id, self.room_id, str(uuid4()), str(uuid4()), start_at, start_at, end_at),
            )
            connection.execute(
                """
                INSERT INTO marketplace_requests (
                    id, user_id, room_id, earliest_start, latest_end, duration_minutes, party_size,
                    equipment, max_price_ore, preferences
                ) VALUES (%s, %s, %s, %s, %s, 30, 2, ARRAY[]::text[], 50000, '')
                """,
                (request_id, self.host.id, self.room_id, start_at, end_at),
            )
            connection.execute(
                """
                INSERT INTO marketplace_offers (
                    id, request_id, opening_id, room_id, start_at, end_at, price_ore, expires_at,
                    match_reason, match_provider, confirmed_at, booking_reference
                ) VALUES (%s, %s, %s, %s, %s, %s, 10000, %s, 'test', 'test', now(), %s)
                """,
                (uuid4(), request_id, opening_id, self.room_id, start_at, end_at, start_at, reference),
            )

    def test_free_room_has_no_booking_or_block(self):
        [room] = self.rooms()
        self.assertIsNone(room.current_booking)
        self.assertIsNone(room.active_block)

    def test_booking_and_block_covering_now_are_reported(self):
        now = datetime.now(UTC)
        db.schedule_device_block(self.room_id, now - timedelta(minutes=5), now + timedelta(minutes=30))
        self.book(now - timedelta(minutes=20), now + timedelta(minutes=40), f"NOW-{uuid4().hex[:8]}")
        self.book(now + timedelta(hours=2), now + timedelta(hours=3), f"LATER-{uuid4().hex[:8]}")

        [room] = self.rooms()
        self.assertTrue(room.current_booking.reference.startswith("NOW-"))
        self.assertGreater(room.current_booking.end_at, now)
        self.assertLess(room.active_block.start_at, now)
        self.assertGreater(room.active_block.end_at, now)

    def test_public_live_view_shows_demo_room_without_personal_data(self):
        claim_demo_rooms(f"live-{uuid4().hex}@example.test", "a-long-test-password")
        now = datetime.now(UTC)
        db.record_occupancy({
            "source": "test", "event_id": str(uuid4()), "external_room_id": "digs-demo-1",
            "occupied": True, "changed_at": now.isoformat(),
        })
        payload = LiveRoom.model_validate(live_room("digs-demo-1", Response())).model_dump()
        self.assertTrue(payload["last_occupancy"]["occupied"])
        self.assertNotIn("reference", str(payload))
        with self.assertRaises(HTTPException) as raised:
            live_room(self.room_id, Response())
        self.assertEqual(raised.exception.status_code, 404)

    def test_demo_host_claims_digs_rooms_idempotently(self):
        email = f"demo-{uuid4().hex}@example.test"
        first = claim_demo_rooms(email, "a-long-test-password")
        self.assertIn("digs-demo-1", first)
        self.assertEqual(claim_demo_rooms(email, None), first)


class PublicLiveRoomTests(unittest.TestCase):
    def test_only_demo_rooms_are_public(self):
        with self.assertRaises(HTTPException) as raised:
            live_room("not-a-demo-room", Response())
        self.assertEqual(raised.exception.status_code, 404)

    def test_live_room_drops_booking_reference(self):
        now = datetime.now(UTC).isoformat()
        room = LiveRoom.model_validate({
            "id": "digs-demo-1", "name": "Driv", "venue": "Digs",
            "current_booking": {"start_at": now, "end_at": now, "reference": "SECRET"},
        })
        self.assertNotIn("SECRET", room.model_dump_json())
