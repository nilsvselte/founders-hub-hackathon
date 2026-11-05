import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app import db


@unittest.skipUnless(os.environ.get("MARKETPLACE_TEST_DATABASE_URL"), "requires disposable PostgreSQL")
class BookingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        admin_dsn = os.environ["MARKETPLACE_TEST_DATABASE_URL"]
        schema_name = f"booking_test_{uuid4().hex}"
        schema = sql.Identifier(schema_name)
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))

        def drop_schema():
            with psycopg.connect(admin_dsn, autocommit=True) as connection:
                connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))

        cls.addClassCleanup(drop_schema)
        cls.dsn = make_conninfo(
            admin_dsn, options=f"-csearch_path={schema_name}", application_name=schema_name
        )
        environment = patch.dict(os.environ, {"DATABASE_URL": cls.dsn, "MARKETPLACE_TURNAROUND_MINUTES": "2"})
        environment.start()
        cls.addClassCleanup(environment.stop)
        db.check_ready()

    def setUp(self):
        self.room_id = f"booking-test-{uuid4().hex}"
        self.renter, self.other_renter = uuid4(), uuid4()
        self.start = datetime.now(UTC) + timedelta(minutes=10)
        self.end = self.start + timedelta(minutes=30)
        self.event = {
            "external_room_id": self.room_id,
            "event_id": str(uuid4()),
            "block_id": str(uuid4()),
            "source": "test",
            "released_at": datetime.now(UTC),
            "scheduled_end_at": self.end,
        }
        with db._connect() as connection:
            connection.execute(
                """
                INSERT INTO marketplace_rooms (
                    id, name, city, venue_name, kind, description, image_key, capacity, equipment,
                    hourly_rate_ore, minimum_hourly_rate_ore, maximum_hourly_rate_ore, published
                )
                VALUES (%s, 'Test room', 'Trondheim', 'Test venue', 'Meeting room', 'Test',
                        'none', 8, ARRAY['screen'], 20000, 10000, 40000, true)
                """,
                (self.room_id,),
            )
            for renter in (self.renter, self.other_renter):
                connection.execute(
                    """
                    INSERT INTO marketplace_users (id, name, email, password_salt, password_hash)
                    VALUES (%s, 'Test renter', %s, %s, %s)
                    """,
                    (renter, f"{renter}@example.test", bytes(16), bytes(32)),
                )

    def request(self, renter=None, *, max_price_ore=30000, duration_minutes=30):
        return db.create_request(
            {
                "room_id": self.room_id,
                "earliest_start": self.start,
                "latest_end": self.end,
                "duration_minutes": duration_minutes,
                "party_size": 4,
                "equipment": ["screen"],
                "max_price_ore": max_price_ore,
                "preferences": "",
            },
            renter or self.renter,
        )

    def hold(self, request_id):
        candidate, = db.list_candidates(request_id)
        offer = db.create_offer(request_id, candidate, "Matches requested time", "test")
        self.assertIsNotNone(offer)
        return offer

    def test_concurrent_release_hold_and_accept_are_idempotent(self):
        with ThreadPoolExecutor(max_workers=16) as workers:
            releases = list(workers.map(lambda _: db.record_release(self.event), range(48)))
            self.assertEqual(sum(release["created"] for release in releases), 1)
            self.assertEqual(len({release["opening_id"] for release in releases}), 1)

            requests = [self.request() for _ in range(48)]
            candidate, = db.list_candidates(requests[0])
            offers = list(workers.map(
                lambda request_id: db.create_offer(request_id, candidate, "Matches requested time", "test"),
                requests,
            ))
            (request_id, offer), = [(request_id, offer) for request_id, offer in zip(requests, offers) if offer]

            self.assertIsNone(db.get_request(request_id, user_id=self.other_renter))
            with self.assertRaises(db.NotFound):
                db.accept_offer(request_id, offer["id"], user_id=self.other_renter)

            with db._connect() as connection:
                connection.execute(
                    "UPDATE marketplace_rooms SET hourly_rate_ore = 35000 WHERE id = %s",
                    (self.room_id,),
                )
            bookings = list(workers.map(
                lambda _: db.accept_offer(request_id, offer["id"], user_id=self.renter), range(48)
            ))
            self.assertEqual({booking["status"] for booking in bookings}, {"confirmed"})
            references = {booking["booking_reference"] for booking in bookings}
            self.assertEqual(len(references), 1)
            self.assertNotIn(None, references)
            self.assertEqual({booking["offer"]["price_ore"] for booking in bookings}, {offer["price_ore"]})

    def test_expired_offer_frees_the_slot(self):
        db.record_release(self.event)
        request_id = self.request()
        offer = self.hold(request_id)
        with db._connect() as connection:
            connection.execute("UPDATE marketplace_offers SET expires_at = now() WHERE id = %s", (offer["id"],))
        with self.assertRaises(db.Conflict):
            db.accept_offer(request_id, offer["id"], user_id=self.renter)
        replacement = self.hold(self.request(self.other_renter))
        self.assertEqual(replacement["start_at"], offer["start_at"])

    def test_later_rate_band_can_fit_the_request_budget(self):
        oslo = ZoneInfo("Europe/Oslo")
        today = datetime.now(oslo).date()
        monday = today + timedelta(days=7 - today.weekday())
        for day_offset, hour, minutes_to_cheaper_rate, budget, price in [
            (0, 15, 60, 10000, 8500),
            (4, 23, 60, 8250, 8000),
        ]:
            with self.subTest(day_offset=day_offset):
                day = monday + timedelta(days=day_offset)
                self.start = datetime(day.year, day.month, day.day, hour, tzinfo=oslo).astimezone(UTC)
                expected_start = self.start + timedelta(minutes=minutes_to_cheaper_rate)
                self.end = expected_start + timedelta(minutes=30)
                db.record_release({
                    **self.event,
                    "event_id": str(uuid4()),
                    "block_id": str(uuid4()),
                    "scheduled_end_at": self.end,
                })
                offer = self.hold(self.request(max_price_ore=budget))
                self.assertEqual(datetime.fromisoformat(offer["start_at"]), expected_start)
                self.assertEqual(datetime.fromisoformat(offer["end_at"]), self.end)
                self.assertEqual(offer["price_ore"], price)

    def test_booking_keeps_elapsed_duration_across_the_oslo_clock_change(self):
        oslo = ZoneInfo("Europe/Oslo")
        today = datetime.now(oslo).date()
        march_end = date(today.year, 3, 31)
        sunday = march_end - timedelta(days=(march_end.weekday() + 1) % 7)
        if sunday <= today:
            march_end = date(today.year + 1, 3, 31)
            sunday = march_end - timedelta(days=(march_end.weekday() + 1) % 7)
        self.start = datetime(sunday.year, 3, sunday.day, 1, 45, tzinfo=oslo).astimezone(UTC)
        self.end = self.start + timedelta(hours=2)
        db.record_release({**self.event, "scheduled_end_at": self.end})
        request_id = self.request(max_price_ore=40000, duration_minutes=120)
        offer = self.hold(request_id)
        booking = db.accept_offer(request_id, offer["id"], user_id=self.renter)
        self.assertEqual(booking["status"], "confirmed")
        self.assertEqual(datetime.fromisoformat(booking["offer"]["end_at"]), self.end)
        saved, = db.list_requests(self.renter)
        self.assertEqual(saved["booking_reference"], booking["booking_reference"])
        self.assertEqual(saved["offer"]["room_venue"], "Test venue")
        self.assertEqual(saved["offer"]["room_city"], "Trondheim")

    def test_accept_observes_hold_invalidated_while_waiting_for_room_lock(self):
        db.record_release(self.event)
        request_id = self.request()
        offer = self.hold(request_id)

        with ThreadPoolExecutor(max_workers=1) as workers:
            with db._connect() as host:
                # Same lock order and invalidation as the host listing update.
                host.execute("SELECT id FROM marketplace_rooms WHERE id = %s FOR UPDATE", (self.room_id,))
                host.execute("UPDATE marketplace_rooms SET capacity = 1 WHERE id = %s", (self.room_id,))
                host.execute("UPDATE marketplace_offers SET expires_at = now() WHERE id = %s", (offer["id"],))
                acceptance = workers.submit(db.accept_offer, request_id, offer["id"], user_id=self.renter)

                with psycopg.connect(self.dsn, autocommit=True) as observer:
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        waiting, = observer.execute(
                            """
                            SELECT EXISTS (
                                SELECT 1 FROM pg_stat_activity
                                WHERE application_name = current_setting('application_name')
                                  AND %s = ANY(pg_blocking_pids(pid))
                            )
                            """,
                            (host.info.backend_pid,),
                        ).fetchone()
                        if waiting:
                            break
                        time.sleep(0.01)
                    else:
                        self.fail("acceptance did not wait for the host's room lock")

            with self.assertRaises(db.Conflict):
                acceptance.result(timeout=5)
        self.assertEqual(db.get_request(request_id, user_id=self.renter)["status"], "waiting")
