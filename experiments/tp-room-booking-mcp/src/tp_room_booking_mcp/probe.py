"""Read-only live compatibility probe. Never sends POST, PUT, PATCH or DELETE."""

import argparse
import asyncio
import json

from .client import Settings, TPClient, TPError


async def probe(start: str | None, end: str | None):
    client = TPClient(Settings.from_env())
    try:
        status = await client.session_status()
        locations = await client.list_locations()
        print(
            json.dumps(
                {
                    "session": status,
                    "areas": len(locations["areas"]),
                    "buildings": len(locations["buildings"]),
                },
                indent=2,
            )
        )
        if start and end:
            try:
                rooms = await client.search(start, end)
                print(json.dumps({"availability_response_count": len(rooms)}))
            except TPError as exc:
                print(json.dumps({"availability_error": str(exc)}))
    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    if bool(args.start) != bool(args.end):
        parser.error("Supply both --start and --end.")
    asyncio.run(probe(args.start, args.end))
