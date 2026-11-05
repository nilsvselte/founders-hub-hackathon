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
from app.preferences import put_preferences
from app.schemas import AboutYou, RoomPreferences, UserPreferencesInput
from app.suggestions import SuggestionInput, SuggestionResult, suggest_rooms


@unittest.skipUnless(os.environ.get("MARKETPLACE_TEST_DATABASE_URL"), "requires disposable PostgreSQL")
class SuggestionsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        admin_dsn = os.environ["MARKETPLACE_TEST_DATABASE_URL"]
        schema_name = f"suggestions_test_{uuid4().hex}"
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
        user_id = uuid4()
        self.account = Account(id=user_id, name="Test renter", email=f"{user_id}@example.test", role="renter")
        self.start = datetime.now(UTC) + timedelta(minutes=40)
        self.end = self.start + timedelta(minutes=30)
        with db._connect() as connection:
            connection.execute(
                """
                INSERT INTO marketplace_users (id, name, email, password_salt, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, self.account.name, self.account.email, bytes(16), bytes(32)),
            )

    def room(self, venue="digs", rate=20000, equipment=None, *, released=True, owner_id=None):
        room_id = f"suggestion-test-{uuid4().hex}"
        venue_name = "Independent venue" if owner_id is not None else venue
        with db._connect() as connection:
            connection.execute(
                """
                INSERT INTO marketplace_rooms (
                    id, venue, name, city, venue_name, kind, description, image_key, capacity, equipment,
                    hourly_rate_ore, minimum_hourly_rate_ore, maximum_hourly_rate_ore, published, owner_id
                ) VALUES (%s, %s, 'Test room', 'Trondheim', %s, 'Meeting room', 'Test', 'none',
                          8, %s, %s, %s, %s, true, %s)
                """,
                (room_id, venue, venue_name, ["screen"] if equipment is None else equipment, rate, rate, rate, owner_id),
            )
        if released:
            self.release(room_id)
        return room_id

    def release(self, room_id):
        result = db.record_release({
            "source": "host", "event_id": str(uuid4()), "block_id": str(uuid4()), "external_room_id": room_id,
            "released_at": datetime.now(UTC), "scheduled_end_at": self.end,
        })
        self.assertTrue(result["created"])

    def suggest(self, **fields):
        response = Response()
        body = SuggestionInput(start_at=self.start, end_at=self.end, party_size=4, **fields)
        result = SuggestionResult.model_validate(suggest_rooms(body, response, self.account))
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        return result

    def test_preferences_filter_rank_and_deduplicate_without_creating_a_hold(self):
        preferred = self.room("kowork", 60000)
        cheap = self.room()
        self.release(preferred)
        self.room("brighten", 1000)
        self.room("digs", 1000, [])
        self.room("digs", 100000)
        self.room("digs", 1000, released=False)
        put_preferences(
            UserPreferencesInput(
                about=AboutYou(home_area="Kowork"),
                preferences=RoomPreferences(
                    max_hourly_ore=65000, preferred_venues=["kowork"], avoid_venues=["brighten"],
                    equipment=["screen"], room_kinds=["Meeting Room"],
                ),
            ),
            self.account, Response(),
        )
        with db._connect() as connection:
            requests_before = connection.execute("SELECT count(*) FROM marketplace_requests").fetchone()["count"]
            offers_before = connection.execute("SELECT count(*) FROM marketplace_offers").fetchone()["count"]

        result = self.suggest()
        self.assertEqual([room.room_id for room in result.suggestions], [preferred, cheap])
        first, second = result.suggestions
        self.assertEqual(first.address, "Kjøpmannsgata 40, Trondheim")
        self.assertIsNone(second.address)
        self.assertEqual((first.start_at, first.end_at, first.price_ore), (self.start, self.end, 30000))
        self.assertIn("Matches your preferred area.", first.reason)
        self.assertIn("Matches your preferred room type.", first.reason)
        self.assertEqual(self.suggest(rough_area="Digs").suggestions[0].room_id, cheap)
        self.assertEqual([room.room_id for room in self.suggest(max_price_ore=15000).suggestions], [cheap])
        with db._connect() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM marketplace_requests").fetchone()["count"], requests_before)
            self.assertEqual(connection.execute("SELECT count(*) FROM marketplace_offers").fetchone()["count"], offers_before)

    def test_active_hold_and_host_block_hide_released_rooms(self):
        held_room = self.room()
        blocked_room = self.room()
        db.schedule_device_block(blocked_room, self.start, self.end)
        request_id = db.create_request({
            "room_id": held_room, "earliest_start": self.start, "latest_end": self.end,
            "duration_minutes": 30, "party_size": 4, "equipment": ["screen"],
            "max_price_ore": 30000, "preferences": "",
        }, self.account.id)
        candidate, = db.list_candidates(request_id)
        self.assertIsNotNone(db.create_offer(request_id, candidate, "Fits", "demo"))

        result = self.suggest()
        self.assertEqual(result.suggestions, [])
        self.assertIn("No released room", result.message)

    def test_host_room_does_not_inherit_catalog_venue_preferences_or_address(self):
        host_id = uuid4()
        with db._connect() as connection:
            connection.execute(
                """
                INSERT INTO marketplace_users (id, name, email, password_salt, password_hash, role)
                VALUES (%s, 'Test host', %s, %s, %s, 'host')
                """,
                (host_id, f"{host_id}@example.test", bytes(16), bytes(32)),
            )
        host_room = self.room(owner_id=host_id)
        self.room()
        put_preferences(
            UserPreferencesInput(preferences=RoomPreferences(avoid_venues=["digs"])),
            self.account, Response(),
        )

        suggestion, = self.suggest().suggestions
        self.assertEqual(suggestion.room_id, host_room)
        self.assertIsNone(suggestion.venue_id)
        self.assertIsNone(suggestion.address)
