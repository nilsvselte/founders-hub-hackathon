import json
import os
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import psycopg

from app.main import app


class DeviceWebhookTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {
            "DATABASE_URL": "unused-by-mocked-device-tests",
            "MARKETPLACE_DEVICE_ADAPTER": "atech",
            "MARKETPLACE_DEVICE_TOKEN": "webhook-test-token",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.event = {"external_room_id": "digs-demo-1", "event_id": str(uuid4())}

    async def post(self, payload, token="webhook-test-token"):
        headers = [(b"content-type", b"application/json")]
        if token is not None:
            headers.append((b"authorization", f"Bearer {token}".encode()))
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/internal/device/events",
            "query_string": b"",
            "headers": headers,
        }
        messages = []

        async def receive():
            return {"type": "http.request", "body": json.dumps(payload).encode()}

        async def send(message):
            messages.append(message)

        await app(scope, receive, send)
        return messages[0]["status"], json.loads(messages[1]["body"])

    async def test_authenticated_release_request_looks_up_a_block_and_wakes_matching(self):
        opening_id = str(uuid4())
        payload = {
            **self.event, "type": "room.release_requested",
            "requested_at": "2026-11-05T17:00:00+01:00",
            "scheduled_end_at": "2026-11-06T17:00:00+01:00",  # Not authoritative.
        }
        with (
            patch("app.main.db.record_release_request",
                  return_value={"created": True, "opening_id": opening_id}) as record,
            patch("app.main.db.list_pending_request_ids", return_value=["waiting-request"]) as pending,
            patch("app.main.run_match_in_background") as match,
        ):
            status, result = await self.post(payload)

        self.assertEqual(status, 200)
        self.assertEqual(result["opening_id"], opening_id)
        record.assert_called_once_with({
            **self.event, "source": "atech", "type": "room.release_requested",
            "requested_at": datetime(2026, 11, 5, 16, tzinfo=UTC),
        })
        pending.assert_called_once_with("digs-demo-1")
        match.assert_called_once_with("waiting-request")

    async def test_retry_can_wake_matching_after_the_opening_already_committed(self):
        opening_id = str(uuid4())
        payload = {**self.event, "type": "room.release_requested", "requested_at": "2026-11-05T16:00:00Z"}
        with (
            patch("app.main.db.record_release_request", side_effect=[
                {"created": True, "opening_id": opening_id},
                {"created": False, "opening_id": opening_id, "reason": "duplicate_event"},
            ]),
            patch("app.main.db.list_pending_request_ids", side_effect=[
                psycopg.OperationalError("transient DB failure"), ["waiting-request"],
            ]),
            patch("app.main.run_match_in_background") as match,
        ):
            status, _ = await self.post(payload)
            self.assertEqual(status, 503)
            status, result = await self.post(payload)

        self.assertEqual(status, 200)
        self.assertFalse(result["created"])
        self.assertEqual(result["opening_id"], opening_id)
        match.assert_called_once_with("waiting-request")

    async def test_occupancy_does_not_open_inventory_or_wake_matching(self):
        payload = {
            **self.event, "type": "room.occupancy_changed", "occupied": False,
            "changed_at": "2026-11-05T17:00:00+01:00",
        }
        with (
            patch("app.main.db.record_occupancy",
                  return_value={"created": False, "reason": "occupancy_recorded"}) as record,
            patch("app.main.db.record_release") as release,
            patch("app.main.run_match_in_background") as match,
        ):
            status, result = await self.post(payload)

        self.assertEqual(status, 200)
        self.assertFalse(result["created"])
        record.assert_called_once_with({
            **self.event, "source": "atech", "type": "room.occupancy_changed", "occupied": False,
            "changed_at": datetime(2026, 11, 5, 16, tzinfo=UTC),
        })
        release.assert_not_called()
        match.assert_not_called()

    async def test_authentication_and_payload_validation_precede_persistence(self):
        payload = {
            **self.event, "type": "room.occupancy_changed", "occupied": False,
            "changed_at": "2026-11-05T17:00:00+01:00",
        }
        with patch("app.main.db.record_occupancy") as record:
            status, _ = await self.post(payload, token=None)
            self.assertEqual(status, 401)
            for field, value in (("occupied", 0), ("changed_at", "2026-11-05T17:00:00"),
                                 ("event_id", "bad\0id"), ("event_id", chr(0xD800))):
                with self.subTest(field=field):
                    status, _ = await self.post({**payload, field: value})
                    self.assertEqual(status, 422)
        record.assert_not_called()

    async def test_original_adapter_factory_still_ingests_explicit_releases(self):
        payload = {
            **self.event, "type": "room.released", "block_id": str(uuid4()),
            "released_at": "2026-11-05T16:00:00Z", "scheduled_end_at": "2026-11-05T17:00:00Z",
        }
        with (
            patch.dict(os.environ, {"MARKETPLACE_DEVICE_ADAPTER": "app.device:FixtureDeviceAdapter"}),
            patch("app.main.db.record_release", return_value={"created": False}) as record,
        ):
            status, _ = await self.post(payload)

        self.assertEqual(status, 200)
        self.assertEqual(record.call_args.args[0]["block_id"], payload["block_id"])
        self.assertEqual(record.call_args.args[0]["source"], "fixture")
