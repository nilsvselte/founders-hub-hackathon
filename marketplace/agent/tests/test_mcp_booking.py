import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ElicitResult

from mcp_server.server import RoomApproval, Runtime, confirm_booking, get_preferences, hold_room


REQUEST_ID = UUID(int=1)
OFFER_ID = UUID(int=2)
REPLACEMENT_ID = UUID(int=3)
APPROVAL = RoomApproval(
    room_id="digs-demo-1", start_at="2027-01-03T12:00:00+01:00",
    end_at="2027-01-03T13:00:00+01:00", max_price_ore=35000,
)


def status(offer_id=OFFER_ID, price=35000, start_at="2027-01-03T11:00:00Z"):
    return {
        "id": str(REQUEST_ID), "room_id": APPROVAL.room_id, "status": "offered", "auto_confirm": False,
        "earliest_start": "2027-01-03T11:00:00Z", "latest_end": "2027-01-03T12:00:00Z",
        "max_price_ore": APPROVAL.max_price_ore,
        "offer": {"id": str(offer_id), "price_ore": price, "start_at": start_at, "end_at": "2027-01-03T12:00:00Z"},
    }


class MCPBookingTest(unittest.IsolatedAsyncioTestCase):
    async def make_context(self, handle):
        client = httpx.AsyncClient(
            base_url="http://127.0.0.1:8001", transport=httpx.MockTransport(handle),
        )
        self.addAsyncCleanup(client.aclose)
        return SimpleNamespace(
            session=SimpleNamespace(client_params=None),
            request_context=SimpleNamespace(lifespan_context=Runtime(client, asyncio.Lock())),
        )

    async def test_hold_requires_approval_and_uses_exact_booking_window(self):
        calls = []

        def handle(request):
            calls.append(request)
            if request.method == "POST":
                self.assertEqual(json.loads(request.content), {
                    "room_id": "digs-demo-1", "auto_confirm": False, "earliest_start": "2027-01-03T12:00:00+01:00",
                    "latest_end": "2027-01-03T13:00:00+01:00", "duration_minutes": 60,
                    "party_size": 4, "max_price_ore": 35000, "equipment": ["screen"],
                })
                return httpx.Response(201, json={"id": str(REQUEST_ID)})
            return httpx.Response(200, json=status())

        ctx = await self.make_context(handle)
        with self.assertRaisesRegex(ToolError, "Ask the renter"):
            await hold_room(ctx, APPROVAL, 4, False)
        self.assertEqual(calls, [])
        result = await hold_room(ctx, APPROVAL, 4, True, ["screen"])
        self.assertEqual(result["offer"]["id"], str(OFFER_ID))

    async def test_confirm_retries_conflict_once_and_checks_replacement(self):
        for changed_time in (False, True):
            with self.subTest(changed_time=changed_time):
                mutations = []

                def handle(request):
                    if request.method == "GET":
                        if not mutations:
                            return httpx.Response(200, json=status())
                        replacement = status(
                            REPLACEMENT_ID, price=34000,
                            start_at="2027-01-03T11:01:00Z" if changed_time else "2027-01-03T11:00:00Z",
                        )
                        return httpx.Response(200, json=replacement)
                    mutations.append(request.url.path)
                    if len(mutations) == 1:
                        return httpx.Response(409)
                    if request.url.path.endswith("/retry"):
                        return httpx.Response(200, json={**status(), "status": "waiting", "offer": None})
                    return httpx.Response(200, json={
                        **status(REPLACEMENT_ID), "status": "confirmed", "booking_reference": "DEMO-123",
                    })

                ctx = await self.make_context(handle)
                first = f"/standby-requests/{REQUEST_ID}/offers/{OFFER_ID}/accept"
                retry = f"/standby-requests/{REQUEST_ID}/retry"
                replacement = f"/standby-requests/{REQUEST_ID}/offers/{REPLACEMENT_ID}/accept"
                if changed_time:
                    with self.assertRaisesRegex(ToolError, "differs from the approved time or price"):
                        await confirm_booking(ctx, REQUEST_ID, APPROVAL, True)
                    self.assertEqual(mutations, [first, retry])
                else:
                    result = await confirm_booking(ctx, REQUEST_ID, APPROVAL, True)
                    self.assertEqual(result["booking_reference"], "DEMO-123")
                    self.assertEqual(mutations, [first, retry, replacement])

    async def test_confirm_refuses_an_offer_above_the_ceiling(self):
        def handle(request):
            self.assertEqual(request.method, "GET")
            return httpx.Response(200, json=status(price=35001))

        ctx = await self.make_context(handle)
        with self.assertRaisesRegex(ToolError, "differs from the approved time or price"):
            await confirm_booking(ctx, REQUEST_ID, APPROVAL, True)

    async def test_confirm_refuses_a_browser_auto_booking_request(self):
        def handle(request):
            self.assertEqual(request.method, "GET")
            return httpx.Response(200, json={**status(), "auto_confirm": True})

        ctx = await self.make_context(handle)
        with self.assertRaisesRegex(ToolError, "separate hold and confirmation flow"):
            await confirm_booking(ctx, REQUEST_ID, APPROVAL, True)

    async def test_preferences_use_the_agent_context_endpoint(self):
        shared = {"hard_filters": {"default_equipment": ["screen"]}}

        def handle(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/me/agent-context")
            return httpx.Response(200, json=shared)

        ctx = await self.make_context(handle)
        self.assertEqual(await get_preferences(ctx), shared)

    async def test_stdio_lists_tools_and_approval_hints(self):
        approval_messages = []

        async def decline(_context, request):
            approval_messages.append(request.message)
            return ElicitResult(action="decline")

        params = StdioServerParameters(
            command=sys.executable, args=["-m", "mcp_server.server"],
            cwd=Path(__file__).resolve().parents[1],
            env={
                **os.environ, "MARKETPLACE_API_TOKEN": "fake-local-test-token",
                "MARKETPLACE_API_URL": "http://127.0.0.1:1",
            },
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, elicitation_callback=decline) as client:
                await client.initialize()
                listed = await client.list_tools()
                declined = await client.call_tool("hold_room", {
                    "approval": APPROVAL.model_dump(mode="json"), "party_size": 4, "approved": True,
                })
        self.assertTrue(declined.isError)
        self.assertIn("did not approve", declined.content[0].text)
        self.assertEqual(len(approval_messages), 1)
        self.assertIn("digs-demo-1", approval_messages[0])
        self.assertIn("NOK 350.00", approval_messages[0])
        tools = {tool.name: tool for tool in listed.tools}
        self.assertEqual(set(tools), {
            "search_rooms", "quote_room", "suggest_rooms", "get_preferences",
            "hold_room", "confirm_booking", "list_bookings",
        })
        for name, tool in tools.items():
            destructive = name in {"hold_room", "confirm_booking"}
            self.assertEqual(tool.annotations.readOnlyHint, not destructive)
            self.assertEqual(tool.annotations.destructiveHint, destructive)
            self.assertNotIn("ctx", tool.inputSchema["properties"])
