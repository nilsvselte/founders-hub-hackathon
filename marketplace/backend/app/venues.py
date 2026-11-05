"""Venues the marketplace can serve.

MARKETPLACE_VENUE selects the metadata and default fixture room for the preview.
The public room catalog can show several venues in the same deployment.
"""

import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Venue:
    id: str
    operator: str
    name: str
    location: str
    booking_prefix: str
    demo_room_id: str

    def public(self) -> dict[str, str]:
        data = asdict(self)
        del data["booking_prefix"], data["demo_room_id"]
        return data


VENUES = {
    venue.id: venue
    for venue in (
        Venue(
            id="digs",
            operator="Mesh",
            name="Digs",
            location="Digs, Trondheim",
            booking_prefix="MESH",
            demo_room_id="digs-demo-1",
        ),
        Venue(
            id="kowork",
            operator="Kowork",
            name="Kowork",
            location="Kjøpmannsgata 40, Trondheim",
            booking_prefix="KOWORK",
            demo_room_id="kowork-meeting-room",
        ),
        Venue(
            id="brighten",
            operator="Brighten",
            name="Brighten",
            location="Bakke Bydelshus, Nordre Berggate 2, Trondheim",
            booking_prefix="BRIGHTEN",
            demo_room_id="brighten-meeting-room",
        ),
    )
}


def venue(venue_id: str) -> Venue:
    try:
        return VENUES[venue_id]
    except KeyError:
        raise RuntimeError(f"Unknown venue {venue_id!r}") from None


def current_venue() -> Venue:
    return venue(os.getenv("MARKETPLACE_VENUE", "digs").strip() or "digs")
