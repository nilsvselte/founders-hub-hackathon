"""Venues the marketplace can serve.

Each deployment serves one venue, chosen with MARKETPLACE_VENUE. Rooms and
standby requests carry their venue, so a request is only matched to rooms at
the venue where it was made, even when several venues share one database.
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
    )
}


def venue(venue_id: str) -> Venue:
    try:
        return VENUES[venue_id]
    except KeyError:
        raise RuntimeError(f"Unknown venue {venue_id!r}") from None


def current_venue() -> Venue:
    return venue(os.getenv("MARKETPLACE_VENUE", "digs").strip() or "digs")
