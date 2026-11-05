import json
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

import psycopg
from fastapi import FastAPI
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app import accounts, db, preferences
from app.schemas import UserPreferences


@unittest.skipUnless(os.environ.get("MARKETPLACE_TEST_DATABASE_URL"), "requires disposable PostgreSQL")
class PreferencesTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        admin_dsn = os.environ["MARKETPLACE_TEST_DATABASE_URL"]
        schema_name = f"preferences_test_{uuid4().hex}"
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
        cls.app = FastAPI()
        cls.app.include_router(accounts.router)
        cls.app.include_router(preferences.router)

    async def call(self, method, path, *, body=None, cookie=None, token=None, mutation=True):
        headers = [(b"content-type", b"application/json")]
        if mutation:
            headers.append((b"x-marketplace-request", b"1"))
        if cookie:
            headers.append((b"cookie", cookie))
        if token:
            headers.append((b"authorization", f"Bearer {token}".encode()))
        scope = {"type": "http", "method": method, "path": path, "query_string": b"", "headers": headers}
        messages = []

        async def receive():
            return {"type": "http.request", "body": json.dumps(body).encode() if body is not None else b""}

        async def send(message):
            messages.append(message)

        await self.app(scope, receive, send)
        data = messages[1]["body"]
        return messages[0]["status"], dict(messages[0]["headers"]), json.loads(data) if data else None

    async def register(self, role="renter"):
        status, headers, user = await self.call("POST", "/auth/register", body={
            "name": "Preferences test",
            "email": f"{uuid4().hex}@example.test",
            "password": "fixture-password-preferences-test",
            "role": role,
        })
        self.assertEqual(status, 201)
        return headers[b"set-cookie"].split(b";", 1)[0], user["id"]

    async def test_account_scope_cookie_mutation_and_agent_read(self):
        path = "/me/preferences"
        context_path = "/me/agent-context"
        renter, renter_id = await self.register()
        other, _ = await self.register()
        host, _ = await self.register("host")
        self.assertEqual((await self.call("GET", path))[0], 401)
        self.assertEqual((await self.call("GET", path, cookie=host))[0], 403)
        self.assertEqual((await self.call("GET", context_path, cookie=host))[0], 403)
        self.assertEqual((await self.call("PUT", path, cookie=host, body={}))[0], 403)
        self.assertEqual((await self.call("PUT", path, cookie=renter, body={}, mutation=False))[0], 403)

        defaults = UserPreferences().model_dump(mode="json")
        status, headers, result = await self.call("GET", path, cookie=renter)
        self.assertEqual((status, result), (200, defaults))
        self.assertEqual(headers[b"cache-control"], b"no-store")

        payload = {
            "about": {
                "team_name": "Private fixture team",
                "home_area": "Trondheim",
                "home_lat": 63.43123,
                "home_lon": 10.39876,
                "agent_notes": "Quiet, please.",
            },
            "preferences": {
                "max_hourly_ore": 40_000,
                "equipment": [" Screen ", "screen", "Video-conferencing"],
                "room_kinds": [" Meeting room "],
                "preferred_venues": [" digs ", "kowork", "digs"],
                "avoid_venues": ["brighten"],
                "max_travel_minutes": 20,
            },
            "agent": {"notification_channels": ["email"]},
        }
        status, headers, result = await self.call("PUT", path, cookie=renter, body=payload)
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(result["preferences"]["equipment"], ["screen", "video conferencing"])
        self.assertEqual(result["preferences"]["room_kinds"], ["Meeting room"])
        self.assertEqual(result["preferences"]["preferred_venues"], ["digs", "kowork"])
        self.assertEqual(result, preferences.load_preferences(UUID(renter_id)).model_dump(mode="json"))
        self.assertEqual((await self.call("GET", path, cookie=other))[2], defaults)

        status, _, credential = await self.call("POST", "/auth/agent-token", cookie=renter)
        self.assertEqual(status, 201)
        token = credential["token"]
        self.assertEqual((await self.call("GET", path, token=token))[0], 401)
        self.assertEqual((await self.call("PUT", path, body={}, token=token))[0], 401)
        status, headers, context = await self.call("GET", context_path, token=token)
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertTrue(context["has_saved_preferences"])
        self.assertEqual(context["about"]["home"], {"area": "Trondheim", "lat": 63.43, "lon": 10.4})
        self.assertEqual(context["hard_filters"]["must_have_equipment"], ["screen", "video conferencing"])
        self.assertEqual(context["notifications"]["channels"], [])
        serialized_context = json.dumps(context)
        for private in ("Private fixture team", "team_name", renter_id, "63.43123", "10.39876", "email"):
            self.assertNotIn(private, serialized_context)
        self.assertFalse((await self.call("GET", context_path, cookie=other))[2]["has_saved_preferences"])

        status, _, replaced = await self.call("PUT", path, cookie=renter, body={"about": {"agent_notes": "Updated"}})
        self.assertEqual(status, 200)
        self.assertIsNotNone(replaced.pop("updated_at"))
        defaults.pop("updated_at")
        defaults["about"]["agent_notes"] = "Updated"
        self.assertEqual(replaced, defaults)

    async def test_invalid_payloads_do_not_expose_preference_text(self):
        cookie, _ = await self.register()
        marker = "private fixture preference"
        for invalid in (
            {"preferences": {"max_hourly_ore": -1}},
            {"about": {"agent_notes": marker, "home_lat": 63.43}},
            {"preferences": {"preferred_venues": ["digs"], "avoid_venues": ["digs"]}},
            {"about": {"agent_notes": marker + "\0"}},
            {"preferences": {"equipment": [chr(0xD800)]}},
        ):
            with self.subTest(invalid=invalid):
                status, headers, response = await self.call(
                    "PUT", "/me/preferences", cookie=cookie, body={"about": {"agent_notes": marker}, **invalid},
                )
                self.assertEqual(status, 422)
                self.assertEqual(headers[b"cache-control"], b"no-store")
                self.assertEqual(response, {"detail": "Enter valid room preferences"})
