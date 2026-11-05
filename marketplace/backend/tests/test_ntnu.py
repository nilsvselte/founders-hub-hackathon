import os
import tempfile
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException

from app import ntnu, ntnu_access


class NTNUFeatureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            "NTNU_INTEGRATION_FACTORY": "", "NTNU_DEMO_ENABLED": "1",
            "NTNU_DEMO_DIRECTORY": self.directory.name,
        })
        self.environment.start()
        ntnu.conversations.clear()
        self.app = FastAPI()
        self.app.include_router(ntnu.router)
        self.client = self.browser()
        tomorrow = datetime.now(ZoneInfo("Europe/Oslo")).date() + timedelta(days=1)
        self.message = f"6 people in Realfagbygget on {tomorrow} at 08:00 for 1 hour"

    def browser(self):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),
                                 base_url="http://test", headers={"X-Marketplace-Request": "1"})

    async def asyncTearDown(self):
        await self.client.aclose()
        self.environment.stop()
        self.directory.cleanup()
        ntnu.conversations.clear()

    async def search(self, client=None):
        response = await (client or self.client).post("/ntnu/agent", json={
            "mode": "demo", "message": self.message,
        })
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["provider"], "guided-demo")
        self.assertEqual(len(result["rooms"]), 2)
        return result

    async def test_demo_round_trip_uses_mcp_and_persists_across_processes(self):
        result = await self.search()
        proposal = result["rooms"][0]["proposal_id"]
        response = await self.client.post("/ntnu/book", json={"mode": "demo", "proposal_id": proposal})
        self.assertEqual(response.status_code, 200, response.text)
        confirmation = response.json()
        self.assertTrue(confirmation["confirmed"])
        self.assertEqual(confirmation["mode"], "demo")
        again = await self.client.post("/ntnu/book", json={"mode": "demo", "proposal_id": proposal})
        self.assertEqual(again.json(), confirmation)
        booked = (await self.client.get("/ntnu/bookings?mode=demo")).json()["bookings"]
        self.assertEqual(len(booked), 1)
        self.assertEqual(booked[0]["id"], confirmation["booking_id"])
        occupied = await self.client.post("/ntnu/agent", json={"mode": "demo", "message": self.message})
        self.assertEqual(len(occupied.json()["rooms"]), 1)
        cancelled = await self.client.post("/ntnu/cancel", json={
            "mode": "demo", "booking_id": confirmation["booking_id"],
        })
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertTrue(cancelled.json()["cancelled"])
        self.assertEqual((await self.client.get("/ntnu/bookings?mode=demo")).json()["bookings"], [])

    async def test_visitors_cannot_use_another_visitors_proposal_or_bookings(self):
        result = await self.search()
        proposal = result["rooms"][0]["proposal_id"]
        booked = (await self.client.post("/ntnu/book", json={"mode": "demo", "proposal_id": proposal})).json()
        async with self.browser() as other:
            foreign_proposal = await other.post("/ntnu/book", json={"mode": "demo", "proposal_id": proposal})
            self.assertEqual(foreign_proposal.status_code, 409)
            self.assertEqual((await other.get("/ntnu/bookings?mode=demo")).json()["bookings"], [])
            foreign_cancel = await other.post("/ntnu/cancel", json={
                "mode": "demo", "booking_id": booked["booking_id"],
            })
            self.assertEqual(foreign_cancel.status_code, 409)
        self.assertEqual(len((await self.client.get("/ntnu/bookings?mode=demo")).json()["bookings"]), 1)

    async def test_live_has_no_fallback_to_demo_or_local_cookie_file(self):
        status = await self.client.get("/ntnu/status")
        self.assertFalse(status.json()["configured"])
        self.assertFalse(status.json()["connected"])
        with patch.object(ntnu, "_session") as session:
            for endpoint, payload in [
                ("agent", {"mode": "live", "message": self.message}),
                ("book", {"mode": "live", "proposal_id": "a" * 32}),
                ("cancel", {"mode": "live", "booking_id": "anything"}),
                ("connect", {}),
            ]:
                response = await self.client.post("/ntnu/" + endpoint, json=payload)
                self.assertEqual(response.status_code, 503, response.text)
            session.assert_not_called()

    async def test_missing_requirements_are_asked_before_search(self):
        with patch.object(ntnu, "_session") as session:
            first = await self.client.post("/ntnu/agent", json={"mode": "demo", "message": "6 people tomorrow"})
            self.assertEqual(first.status_code, 200)
            self.assertIn("duration", first.json()["message"])
            self.assertIn("campus", first.json()["message"])
            self.assertEqual(first.json()["rooms"], [])
            session.assert_not_called()
        second = await self.client.post("/ntnu/agent", json={
            "mode": "demo", "message": "Realfagbygget at 08:00 for 1 hour",
        })
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["request"]["party_size"], 6)
        self.assertEqual(len(second.json()["rooms"]), 2)

    async def test_mutation_requires_browser_header_and_rejects_user_id(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test") as browser:
            response = await browser.post("/ntnu/agent", json={"mode": "demo", "message": self.message})
            self.assertEqual(response.status_code, 403)
        response = await self.client.post("/ntnu/agent", json={
            "mode": "demo", "message": self.message, "user_id": "someone-else",
        })
        self.assertEqual(response.status_code, 422)

    async def test_mock_payload_cannot_be_reported_as_a_live_booking(self):
        session = SimpleNamespace(call_tool=AsyncMock(return_value=SimpleNamespace(
            isError=False, structuredContent={"backend": "fixture", "data": {"booked": True}},
        )))
        with self.assertRaises(HTTPException) as caught:
            await ntnu._tool(session, "live", "book_room")
        self.assertEqual(caught.exception.status_code, 502)

    async def test_disabled_demo_cannot_be_reenabled_by_request_payload(self):
        with patch.dict(os.environ, {"NTNU_DEMO_ENABLED": "0"}):
            response = await self.client.post("/ntnu/agent", json={"mode": "demo", "message": self.message})
            self.assertEqual(response.status_code, 404)

    async def test_connection_redirect_requires_a_trusted_https_origin(self):
        integration = SimpleNamespace(authorize=AsyncMock(return_value="https://untrusted.invalid/login"))
        with patch.object(ntnu_access, "provider", return_value=integration), patch.dict(
            os.environ, {"NTNU_AUTH_ALLOWED_ORIGINS": "https://auth.dataporten.no"}
        ):
            with self.assertRaises(HTTPException):
                await ntnu_access.authorization_url("server-owned-subject")
            integration.authorize.assert_awaited_once_with("server-owned-subject", "/ntnu")
