import json
import os
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import psycopg
from fastapi import FastAPI
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app import accounts, db, notify

VAPID = {"VAPID_PUBLIC_KEY": "test-public", "VAPID_PRIVATE_KEY": "test-private", "VAPID_SUBJECT": "mailto:t@example.test"}


def run_inline(function, *args):
    notify._safe(function, *args)


class NotifyDeliveryTests(unittest.TestCase):
    """notify() with the database and the push sender mocked out."""

    def setUp(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.execute.return_value.fetchall.return_value = [
            {"endpoint": "https://push.example.test/a", "p256dh": "p", "auth": "a"},
            {"endpoint": "https://push.example.test/b", "p256dh": "p", "auth": "a"},
        ]
        for patcher in (
            patch.dict(os.environ, VAPID),
            patch.object(notify, "_background", run_inline),
            patch.object(db, "_connect", return_value=connection),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_switched_off_kind_sends_nothing(self):
        settings = dict.fromkeys(notify.KINDS, True) | {"offer_ready": False}
        with patch.object(notify, "load_settings", return_value=settings), patch.object(notify, "_send") as send:
            notify.notify(uuid4(), "offer_ready", "A room freed up", "Body", "/bookings/x")
            send.assert_not_called()
            notify.notify(uuid4(), "room_booked", "Booked", "Body", "/host")
            self.assertEqual(send.call_count, 2)
            payload = json.loads(send.call_args.args[1])
            self.assertEqual(payload, {"kind": "room_booked", "title": "Booked", "body": "Body", "url": "/host"})

    def test_gone_subscription_is_deleted_and_errors_do_not_raise(self):
        settings = dict.fromkeys(notify.KINDS, True)
        with (
            patch.object(notify, "load_settings", return_value=settings),
            patch.object(notify, "_send", side_effect=[notify.Gone(), RuntimeError("boom")]),
            patch.object(notify, "delete_subscription") as delete,
        ):
            notify.notify(uuid4(), "room_booked", "Booked", "Body", "/host")
        delete.assert_called_once()
        self.assertEqual(delete.call_args.args[1], "https://push.example.test/a")

    def test_missing_keys_sends_nothing(self):
        with (
            patch.dict(os.environ, {"VAPID_PUBLIC_KEY": "", "VAPID_PRIVATE_KEY": ""}),
            patch.object(notify, "load_settings") as settings,
            patch.object(notify, "_send") as send,
        ):
            notify.notify(uuid4(), "room_booked", "Booked", "Body", "/host")
        settings.assert_not_called()
        send.assert_not_called()


@unittest.skipUnless(os.environ.get("MARKETPLACE_TEST_DATABASE_URL"), "requires disposable PostgreSQL")
class NotificationRoutesTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        admin_dsn = os.environ["MARKETPLACE_TEST_DATABASE_URL"]
        schema_name = f"notify_test_{uuid4().hex}"
        schema = sql.Identifier(schema_name)
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))

        def drop_schema():
            with psycopg.connect(admin_dsn, autocommit=True) as connection:
                connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))

        cls.addClassCleanup(drop_schema)
        dsn = make_conninfo(admin_dsn, options=f"-csearch_path={schema_name}")
        environment = patch.dict(os.environ, {"DATABASE_URL": dsn, **VAPID})
        environment.start()
        cls.addClassCleanup(environment.stop)
        db.check_ready()
        cls.app = FastAPI()
        cls.app.include_router(accounts.router)
        cls.app.include_router(notify.router)

    async def call(self, method, path, *, body=None, cookie=None, mutation=True):
        headers = [(b"content-type", b"application/json")]
        if mutation:
            headers.append((b"x-marketplace-request", b"1"))
        if cookie:
            headers.append((b"cookie", cookie))
        scope = {"type": "http", "method": method, "path": path, "query_string": b"", "headers": headers}
        messages = []

        async def receive():
            return {"type": "http.request", "body": json.dumps(body).encode() if body is not None else b""}

        async def send(message):
            messages.append(message)

        await self.app(scope, receive, send)
        data = b"".join(message.get("body", b"") for message in messages[1:])
        return messages[0]["status"], json.loads(data) if data else None

    async def session(self, role="renter"):
        headers = [(b"content-type", b"application/json"), (b"x-marketplace-request", b"1")]
        body = json.dumps({
            "name": "Notify test", "email": f"{uuid4().hex}@example.test",
            "password": "fixture-password-notify-test", "role": role,
        }).encode()
        scope = {"type": "http", "method": "POST", "path": "/auth/register", "query_string": b"", "headers": headers}
        messages = []

        async def receive():
            return {"type": "http.request", "body": body}

        async def send(message):
            messages.append(message)

        await self.app(scope, receive, send)
        self.assertEqual(messages[0]["status"], 201)
        cookie = dict(messages[0]["headers"])[b"set-cookie"].split(b";", 1)[0]
        user = json.loads(b"".join(m.get("body", b"") for m in messages[1:]))
        return cookie, user["id"]

    async def test_requires_sign_in(self):
        self.assertEqual((await self.call("GET", "/notifications/settings"))[0], 401)
        self.assertEqual((await self.call("GET", "/push/public-key"))[0], 401)

    async def test_public_key(self):
        cookie, _ = await self.session()
        self.assertEqual(await self.call("GET", "/push/public-key", cookie=cookie), (200, {"publicKey": "test-public"}))

    async def test_settings_default_on_and_partial_update(self):
        cookie, _ = await self.session("host")
        everything_on = dict.fromkeys(notify.KINDS, True)
        self.assertEqual(await self.call("GET", "/notifications/settings", cookie=cookie), (200, everything_on))
        status, saved = await self.call("PUT", "/notifications/settings", cookie=cookie, body={"booked_empty": False})
        self.assertEqual((status, saved), (200, everything_on | {"booked_empty": False}))
        status, saved = await self.call("PUT", "/notifications/settings", cookie=cookie, body={"room_booked": False})
        self.assertEqual(saved, everything_on | {"booked_empty": False, "room_booked": False})
        self.assertEqual((await self.call("GET", "/notifications/settings", cookie=cookie))[1], saved)
        self.assertEqual((await self.call("PUT", "/notifications/settings", cookie=cookie, body={"nope": True}))[0], 422)
        self.assertEqual(
            (await self.call("PUT", "/notifications/settings", cookie=cookie, body={}, mutation=False))[0], 403,
        )

    async def test_subscription_upsert_and_delete(self):
        cookie, user_id = await self.session()
        other_cookie, other_id = await self.session()
        endpoint = f"https://push.example.test/{uuid4().hex}"
        body = {"endpoint": endpoint, "keys": {"p256dh": "key-1", "auth": "auth-1"}}

        def rows():
            with db._connect() as connection:
                return connection.execute(
                    "SELECT user_id::text, p256dh FROM marketplace_push_subscriptions WHERE endpoint = %s", (endpoint,),
                ).fetchall()

        self.assertEqual((await self.call("POST", "/push/subscriptions", cookie=cookie, body=body))[0], 204)
        body["keys"]["p256dh"] = "key-2"
        self.assertEqual((await self.call("POST", "/push/subscriptions", cookie=cookie, body=body))[0], 204)
        self.assertEqual(rows(), [{"user_id": user_id, "p256dh": "key-2"}])
        # Another account can't delete someone else's device.
        self.assertEqual(
            (await self.call("DELETE", "/push/subscriptions", cookie=other_cookie, body={"endpoint": endpoint}))[0], 204,
        )
        self.assertEqual(len(rows()), 1)
        self.assertEqual(
            (await self.call("DELETE", "/push/subscriptions", cookie=cookie, body={"endpoint": endpoint}))[0], 204,
        )
        self.assertEqual(rows(), [])
        bad = {"endpoint": "http://insecure.example.test", "keys": {"p256dh": "k", "auth": "a"}}
        self.assertEqual((await self.call("POST", "/push/subscriptions", cookie=cookie, body=bad))[0], 422)
        self.assertIsNotNone(other_id)

    async def test_switched_off_kind_is_not_sent(self):
        cookie, user_id = await self.session("host")
        await self.call("POST", "/push/subscriptions", cookie=cookie, body={
            "endpoint": f"https://push.example.test/{uuid4().hex}", "keys": {"p256dh": "k", "auth": "a"},
        })
        await self.call("PUT", "/notifications/settings", cookie=cookie, body={"occupied_unbooked": False})
        with patch.object(notify, "_send") as send:
            notify._deliver(user_id, "occupied_unbooked", "Title", "Body", "/host")
            send.assert_not_called()
            notify._deliver(user_id, "room_booked", "Title", "Body", "/host")
            send.assert_called_once()

    async def test_repeat_window_dedupes(self):
        key = f"occupied_unbooked:{uuid4().hex}"
        with db._connect() as connection:
            self.assertTrue(notify._claim(connection, key, 30))
            self.assertFalse(notify._claim(connection, key, 30))
            self.assertTrue(notify._claim(connection, f"booked_empty:{key}"))
            self.assertFalse(notify._claim(connection, f"booked_empty:{key}"))

    async def test_event_queries_run(self):
        # The trigger lookups parse and run against the real schema; nothing matches here.
        with patch.object(notify, "notify") as sent:
            notify.check_booked_empty()
            notify._occupancy_changed("no-such-room")
            notify._offer_created(str(uuid4()))
            notify._booking_confirmed(str(uuid4()))
        sent.assert_not_called()
