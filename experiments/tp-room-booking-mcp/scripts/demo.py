"""Exercise the MCP server over stdio using synthetic rooms only."""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    start = (datetime.now(ZoneInfo("Europe/Oslo")) + timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    window = {"start": start.isoformat(), "end": (start + timedelta(hours=1)).isoformat()}
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from tp_room_booking_mcp.server import main; main()"],
        env={"TP_BACKEND": "fixture"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                result = await session.call_tool(name, arguments or {})
                if result.isError:
                    raise RuntimeError(result.content)
                print(json.dumps({"tool": name, "result": result.structuredContent}, indent=2))
                return result.structuredContent["data"]

            await call("session_status")
            found = await call("search_available_rooms", {**window, "min_capacity": 8})
            room = found["rooms"][0]
            booked = await call(
                "book_room", {**window, "room_id": room["id"], "name": "MCP experiment"}
            )
            await call("list_my_bookings")
            await call("cancel_booking", {"booking_id": booked["booking_id"]})
            await call("list_my_bookings")


if __name__ == "__main__":
    asyncio.run(main())
