import asyncio
import json
import unittest
from datetime import UTC, datetime, timedelta
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import anyio

from app import main
from app.accounts import Account, require_agent_or_user


class StandbyRoutesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        account = Account(id=uuid4(), name="Test renter", email="renter@example.test", role="renter")
        self.auth = patch.dict(main.app.dependency_overrides, {require_agent_or_user: lambda: account})
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.request_id = str(uuid4())
        earliest = datetime.now(UTC) + timedelta(minutes=5)
        self.body = {
            "earliest_start": earliest.isoformat(),
            "latest_end": (earliest + timedelta(hours=1)).isoformat(),
            "duration_minutes": 30,
            "party_size": 3,
            "equipment": [],
            "max_price_ore": 35000,
            "preferences": "",
        }
        self.status = {
            **self.body, "id": self.request_id, "room_id": None, "room_name": None, "status": "waiting",
        }

    async def request(self, method, path, body=None, *, bearer=False):
        headers = [(b"content-type", b"application/json"), (b"x-marketplace-request", b"1")]
        if bearer:
            headers.append((b"authorization", b"Bearer test-agent-token"))
        scope = {"type": "http", "method": method, "path": path, "query_string": b"", "headers": headers}
        messages = []

        async def receive():
            return {"type": "http.request", "body": json.dumps(body).encode() if body is not None else b""}

        async def send(message):
            messages.append(message)

        await main.app(scope, receive, send)
        return messages[0]["status"], json.loads(messages[1]["body"])

    async def test_browser_defaults_to_auto_confirmation_and_agent_must_request_a_hold(self):
        def read_status(*_args, **_kwargs):
            return {**self.status, "auto_confirm": create.call_args.args[0]["auto_confirm"]}

        with (
            patch.object(main.db, "create_request", return_value=self.request_id) as create,
            patch.object(main.db, "get_request", side_effect=read_status),
            patch.object(main, "run_match_in_background"),
        ):
            path = "/standby-requests"
            code, status = await self.request("POST", path, self.body)
            self.assertEqual(code, 201)
            self.assertTrue(status["auto_confirm"])
            for agent_body in (self.body, {**self.body, "auto_confirm": True}):
                code, _ = await self.request("POST", path, agent_body, bearer=True)
                self.assertEqual(code, 422)
            code, status = await self.request("POST", path, {**self.body, "auto_confirm": False}, bearer=True)
            self.assertEqual(code, 201)
            self.assertFalse(status["auto_confirm"])
            self.assertEqual(create.call_count, 2)

        code, _ = await self.request("POST", "/demo/release", {}, bearer=True)
        self.assertEqual(code, 401)

        with (
            patch.object(main.db, "get_request", return_value={**self.status, "auto_confirm": True}),
            patch.object(main, "run_match_in_background") as match,
        ):
            retry_path = f"/standby-requests/{self.request_id}/retry"
            code, _ = await self.request("POST", retry_path, bearer=True)
            self.assertEqual(code, 403)
            match.assert_not_called()

    async def test_saved_defaults_fill_only_the_fields_left_out(self):
        saved = SimpleNamespace(equipment=["screen"], max_hourly_ore=25001)
        body = {key: value for key, value in self.body.items() if key != "max_price_ore"}
        with (
            patch.object(main.preferences, "load_preferences", return_value=SimpleNamespace(preferences=saved)),
            patch.object(main.db, "create_request", return_value=self.request_id) as create,
            patch.object(main.db, "get_request", return_value=self.status),
            patch.object(main, "run_match_in_background"),
        ):
            code, _ = await self.request("POST", "/standby-requests", body)
            self.assertEqual(code, 201)
            saved_request = create.call_args.args[0]
            self.assertEqual(saved_request["max_price_ore"], 12501)
            self.assertEqual(saved_request["equipment"], [])

            del body["equipment"]
            code, _ = await self.request("POST", "/standby-requests", body)
            self.assertEqual(code, 201)
            self.assertEqual(create.call_args.args[0]["equipment"], ["screen"])

    async def test_a_stalled_model_does_not_consume_the_http_worker_or_queue_duplicate_matching(self):
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        release, finished = Event(), Event()

        def stalled_model(*_args):
            loop.call_soon_threadsafe(entered.set)
            release.wait(5)
            finished.set()
            return None

        # The synchronous HTTP handlers share AnyIO's worker limiter. A matching
        # job must leave that worker free even when the model is stalled.
        limiter = anyio.to_thread.current_default_thread_limiter()
        before = limiter.total_tokens
        limiter.total_tokens = 1
        self.addCleanup(setattr, limiter, "total_tokens", before)
        retry_path = f"/standby-requests/{self.request_id}/retry"

        with (
            patch.object(main.db, "get_request", return_value=self.status),
            patch.object(main.db, "list_candidates", return_value=[{"opening_id": "opening"}]),
            patch.object(main, "select_match", side_effect=stalled_model) as match,
        ):
            first = asyncio.create_task(self.request("POST", retry_path))
            try:
                await asyncio.wait_for(entered.wait(), timeout=2)
                code, health = await asyncio.wait_for(self.request("GET", "/health"), timeout=2)
                self.assertEqual((code, health), (200, {"status": "ok"}))
                code, _ = await asyncio.wait_for(self.request("POST", retry_path), timeout=2)
                self.assertEqual(code, 200)
                self.assertFalse(finished.is_set())
            finally:
                release.set()
                await asyncio.wait_for(first, timeout=5)

            match.assert_called_once()
