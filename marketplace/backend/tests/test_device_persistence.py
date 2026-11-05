import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app import db


@unittest.skipUnless(os.environ.get("MARKETPLACE_TEST_DATABASE_URL"), "requires disposable PostgreSQL")
class DevicePersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        admin_dsn = os.environ["MARKETPLACE_TEST_DATABASE_URL"]
        schema_name = f"device_test_{uuid4().hex}"
        schema = sql.Identifier(schema_name)
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))

        def drop_schema():
            with psycopg.connect(admin_dsn, autocommit=True) as connection:
                connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))

        cls.addClassCleanup(drop_schema)
        dsn = make_conninfo(admin_dsn, options=f"-csearch_path={schema_name}")
        environment = patch.dict(os.environ, {"DATABASE_URL": dsn, "MARKETPLACE_TURNAROUND_MINUTES": "2"})
        environment.start()
        cls.addClassCleanup(environment.stop)
        db.check_ready()

    def setUp(self):
        self.room_id = f"device-test-{uuid4().hex}"
        self.renter = uuid4()
        self.started_at = datetime.now(UTC) - timedelta(minutes=5)
        self.ends_at = self.started_at + timedelta(minutes=45)
        with db._connect() as connection:
            connection.execute(
                """
                INSERT INTO marketplace_rooms (
                    id, name, city, venue_name, kind, description, image_key, capacity, equipment,
                    hourly_rate_ore, minimum_hourly_rate_ore, maximum_hourly_rate_ore, published
                ) VALUES (%s, 'Room', 'Trondheim', 'Venue', 'Meeting room', 'Test',
                          'none', 8, ARRAY['screen'], 20000, 10000, 40000, true)
                """,
                (self.room_id,),
            )
            connection.execute(
                """
                INSERT INTO marketplace_users (id, name, email, password_salt, password_hash)
                VALUES (%s, 'Renter', %s, %s, %s)
                """,
                (self.renter, f"{self.renter}@example.test", bytes(16), bytes(32)),
            )

    def event(self, **details):
        return {"source": "atech", "event_id": str(uuid4()), "external_room_id": self.room_id, **details}

    def request(self):
        return db.create_request({
            "room_id": self.room_id,
            "earliest_start": datetime.now(UTC) + timedelta(seconds=30),
            "latest_end": self.ends_at,
            "duration_minutes": 20,
            "party_size": 4,
            "equipment": ["screen"],
            "max_price_ore": 30000,
            "preferences": "",
        }, self.renter)

    def manual_opening(self):
        return db.record_release(self.event(
            source="host", released_at=datetime.now(UTC), scheduled_end_at=self.ends_at, block_id=str(uuid4()),
        ))

    def test_occupancy_is_ordered_and_cannot_release_a_block(self):
        db.schedule_device_block(self.room_id, self.started_at, self.ends_at)
        latest = datetime.now(UTC)
        current = self.event(occupied=True, changed_at=latest)
        self.assertEqual(db.record_occupancy(current)["reason"], "occupancy_recorded")
        delayed = self.event(occupied=False, changed_at=latest - timedelta(seconds=3))
        self.assertEqual(db.record_occupancy(delayed)["reason"], "stale_occupancy")
        self.assertEqual(db.record_occupancy({**current, "occupied": False})["reason"], "duplicate_event")
        with db._connect() as connection:
            state = connection.execute(
                "SELECT occupied, changed_at FROM marketplace_room_occupancy WHERE room_id = %s",
                (self.room_id,),
            ).fetchone()
            openings = connection.execute(
                "SELECT count(*) FROM marketplace_openings WHERE room_id = %s", (self.room_id,),
            ).fetchone()
        self.assertEqual(state, {"occupied": True, "changed_at": latest})
        self.assertEqual(openings["count"], 0)

    def test_release_requires_a_current_block_and_preserves_turnaround(self):
        self.assertTrue(self.manual_opening()["created"])
        old_press = self.event(requested_at=datetime.now(UTC))
        self.assertEqual(db.record_release_request(old_press)["reason"], "no_active_block")
        block = db.schedule_device_block(self.room_id, self.started_at, self.ends_at)
        self.assertEqual(db.schedule_device_block(self.room_id, self.started_at, self.ends_at), block)
        self.assertEqual(db.record_release_request(old_press)["reason"], "duplicate_event")
        self.assertEqual(db.record_release_request(self.event(requested_at=old_press["requested_at"]))["reason"], "no_active_block")

        request_id = self.request()
        self.assertEqual(db.list_candidates(request_id), [])
        pressed_at = datetime.now(UTC)
        events = [self.event(requested_at=pressed_at) for _ in range(16)]
        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(db.record_release_request, events))
        self.assertEqual(sum(result["created"] for result in results), 1)
        opening_id, = {result["opening_id"] for result in results}
        self.assertEqual(db.record_release_request(events[0])["opening_id"], opening_id)
        with db._connect() as connection:
            opening = connection.execute(
                "SELECT block_id, start_at, end_at FROM marketplace_openings WHERE id = %s", (opening_id,),
            ).fetchone()
        self.assertEqual(opening, {
            "block_id": block["id"], "start_at": pressed_at + timedelta(minutes=2), "end_at": self.ends_at,
        })
        self.assertTrue(db.list_candidates(request_id))
        for candidate in db.list_candidates(request_id):
            self.assertGreaterEqual(datetime.fromisoformat(candidate["start_at"]), opening["start_at"])

    def test_blocks_cannot_displace_an_existing_hold_or_booking(self):
        self.assertTrue(self.manual_opening()["created"])
        request_id = self.request()
        candidate, = db.list_candidates(request_id)
        offer = db.create_offer(request_id, candidate, "Fits", "demo")
        self.assertIsNotNone(offer)
        with self.assertRaises(db.Conflict):
            db.schedule_device_block(self.room_id, self.started_at, self.ends_at)
        self.assertEqual(db.accept_offer(request_id, offer["id"], user_id=self.renter)["status"], "confirmed")
        with self.assertRaises(db.Conflict):
            db.schedule_device_block(self.room_id, self.started_at, self.ends_at)
