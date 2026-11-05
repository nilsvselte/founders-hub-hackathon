"""Check the portable catalog UPDATE statements without a running database server."""

import sqlite3
import unittest
from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "app/migrations/019_verified_remaining_venues.sql"


class CatalogMigrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.addCleanup(self.connection.close)
        self.connection.executescript("""
            CREATE TABLE marketplace_rooms (
                id TEXT PRIMARY KEY, venue TEXT, venue_name TEXT, image_key TEXT,
                owner_id TEXT, description TEXT, published BOOLEAN
            );
        """)

    def room(self, room_id, venue, *, owner=None, published=False, image=None, name="Venue", description="Sample"):
        self.connection.execute(
            "INSERT INTO marketplace_rooms VALUES (?, ?, ?, ?, ?, ?, ?)",
            (room_id, venue, name, image or f"{venue}-venue", owner, description, published),
        )

    def migrate(self):
        self.connection.executescript(MIGRATION.read_text())

    def rows(self):
        return self.connection.execute("SELECT * FROM marketplace_rooms ORDER BY id").fetchall()

    def test_only_verified_seeded_venues_with_photos_are_published(self):
        verified = ["workwork", "spaces-powerhouse", "clarion-trondheim", "britannia",
                    "quality-prinsen", "quality-panorama", "comfort-trondheim", "home-grand-olav"]
        for venue in verified + ["bargaflyt", "comfort-park", "thon-nidaros", "quality-augustin"]:
            self.room(venue, venue)
        self.room("missing-photo", "workwork", image="none")
        self.room("unknown-venue", "unknown")
        self.migrate()
        published = {row[0] for row in self.connection.execute(
            "SELECT id FROM marketplace_rooms WHERE published"
        )}
        self.assertEqual(published, set(verified))

    def test_host_listings_are_unchanged_including_existing_publish_state(self):
        for published in [False, True]:
            self.room(f"host-{published}", "spaces-powerhouse", owner="host-id", published=published,
                      name="Spaces Powerhouse", description="A room managed by its host")
        before = self.rows()
        self.migrate()
        self.assertEqual(self.rows(), before)

    def test_source_corrections_are_repeatable_and_preserve_custom_descriptions(self):
        self.room("spaces-powerhouse-meeting-room", "spaces-powerhouse", name="Spaces Powerhouse",
                  description="A meeting room at Spaces in Powerhouse Brattørkaia, Brattørkaia 17A.")
        self.room("home-grand-olav-meeting-room", "home-grand-olav",
                  description="The hotel's single meeting room seats 12, in the same building as Olavshallen.")
        self.room("clarion-trondheim-meeting-room", "clarion-trondheim", description="Owner-reviewed description")
        self.migrate()
        result = self.rows()
        by_id = {row[0]: row for row in result}
        self.assertEqual(by_id["spaces-powerhouse-meeting-room"][2], "Regus Powerhouse")
        self.assertIn("Regus Powerhouse", by_id["spaces-powerhouse-meeting-room"][5])
        self.assertIn("610 and Frisøren", by_id["home-grand-olav-meeting-room"][5])
        self.assertEqual(by_id["clarion-trondheim-meeting-room"][5], "Owner-reviewed description")
        self.migrate()
        self.assertEqual(self.rows(), result)
