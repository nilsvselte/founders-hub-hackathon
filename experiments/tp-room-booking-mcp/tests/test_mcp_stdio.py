import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_real_mcp_stdio_search_book_list_cancel(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from tp_room_booking_mcp.server import main; main()"],
        env={"TP_BACKEND": "fixture"},
        cwd=str(tmp_path),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            assert len(tools) == 7
            assert "ctx" not in tools["book_room"].inputSchema["properties"]
            assert tools["search_available_rooms"].annotations.readOnlyHint
            assert not tools["book_room"].annotations.readOnlyHint
            assert tools["cancel_booking"].annotations.destructiveHint

            async def call(name, arguments=None):
                result = await session.call_tool(name, arguments or {})
                assert not result.isError, result.content
                assert result.structuredContent["backend"] == "fixture"
                return result.structuredContent["data"]

            assert (await call("session_status"))["authenticated"]
            assert (await call("list_locations"))["areas"][0]["id"] == "DEMO-GLOS"
            window = {"start": "2026-12-01T12:00:00+01:00", "end": "2026-12-01T13:00:00+01:00"}
            found = await call("search_available_rooms", {**window, "min_capacity": 8})
            assert [room["id"] for room in found["rooms"]] == ["DEMO-G2"]
            empty = await call("search_available_rooms", {**window, "area_id": "nonexistent"})
            assert empty["count"] == 0
            booked = await call("book_room", {**window, "room_id": "DEMO-G2", "name": "MCP demo"})
            assert booked["booked"]
            duplicate = await session.call_tool(
                "book_room", {**window, "room_id": "DEMO-G2", "name": "Collision"}
            )
            assert duplicate.isError
            assert len(await call("list_my_bookings")) == 1
            assert (await call("search_available_rooms", {**window, "min_capacity": 8}))[
                "count"
            ] == 0
            assert (await call("cancel_booking", {"booking_id": booked["booking_id"]}))["cancelled"]
            assert await call("list_my_bookings") == []
            assert (await call("search_available_rooms", {**window, "min_capacity": 8}))[
                "count"
            ] == 1
            assert (await call("get_booking_quotas"))["demo"]
            invalid = await session.call_tool(
                "search_available_rooms", {**window, "min_capacity": -1}
            )
            assert invalid.isError
