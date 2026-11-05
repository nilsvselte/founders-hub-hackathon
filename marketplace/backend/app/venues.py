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
        Venue(
            id="workwork",
            operator="Work-Work",
            name="Work-Work",
            location="Munkegata 58, Trondheim",
            booking_prefix="WORKWORK",
            demo_room_id="workwork-meeting-room",
        ),
        Venue(
            id="bargaflyt",
            operator="Barga",
            name="BargaFlyt",
            location="Olav Tryggvasons gate 40, Trondheim",
            booking_prefix="BARGA",
            demo_room_id="bargaflyt-small-room",
        ),
        Venue(
            id="olo",
            operator="OLO",
            name="OLO fellesverksted",
            location="Ormen Langes vei 12, Trondheim",
            booking_prefix="OLO",
            demo_room_id="olo-workshop",
        ),
        Venue(
            id="spaces-powerhouse",
            operator="IWG",
            name="Regus Powerhouse",
            location="Brattørkaia 17A, Trondheim",
            booking_prefix="SPACES",
            demo_room_id="spaces-powerhouse-meeting-room",
        ),
        Venue(
            id="clarion-trondheim",
            operator="Strawberry",
            name="Clarion Hotel Trondheim",
            location="Brattørkaia 1, Trondheim",
            booking_prefix="CLARION",
            demo_room_id="clarion-trondheim-meeting-room",
        ),
        Venue(
            id="radisson-royal-garden",
            operator="Radisson Hotel Group",
            name="Radisson Blu Royal Garden",
            location="Kjøpmannsgata 73, Trondheim",
            booking_prefix="RADISSON",
            demo_room_id="radisson-royal-garden-meeting-room",
        ),
        Venue(
            id="radisson-airport",
            operator="Radisson Hotel Group",
            name="Radisson Blu Hotel Trondheim Airport",
            location="Værnes, Stjørdal",
            booking_prefix="RADISSONAIR",
            demo_room_id="radisson-airport-meeting-room",
        ),
        Venue(
            id="scandic-lerkendal",
            operator="Scandic",
            name="Scandic Lerkendal",
            location="Klæbuveien 127, Trondheim",
            booking_prefix="SCANDICLER",
            demo_room_id="scandic-lerkendal-meeting-room",
        ),
        Venue(
            id="scandic-nidelven",
            operator="Scandic",
            name="Scandic Nidelven",
            location="Havnegata 1–3, Trondheim",
            booking_prefix="SCANDICNID",
            demo_room_id="scandic-nidelven-meeting-room",
        ),
        Venue(
            id="scandic-solsiden",
            operator="Scandic",
            name="Scandic Solsiden",
            location="Beddingen 1, Trondheim",
            booking_prefix="SCANDICSOL",
            demo_room_id="scandic-solsiden-meeting-room",
        ),
        Venue(
            id="scandic-bakklandet",
            operator="Scandic",
            name="Scandic Bakklandet",
            location="Nedre Bakklandet 60, Trondheim",
            booking_prefix="SCANDICBAK",
            demo_room_id="scandic-bakklandet-meeting-room",
        ),
        Venue(
            id="scandic-hell",
            operator="Scandic",
            name="Scandic Hell",
            location="Sandfærhus 22, Stjørdal",
            booking_prefix="SCANDICHEL",
            demo_room_id="scandic-hell-meeting-room",
        ),
        Venue(
            id="britannia",
            operator="Britannia",
            name="Britannia Hotel",
            location="Dronningens gate 5, Trondheim",
            booking_prefix="BRITANNIA",
            demo_room_id="britannia-boardroom",
        ),
        Venue(
            id="quality-prinsen",
            operator="Strawberry",
            name="Quality Hotel Prinsen",
            location="Kongens gate 30, Trondheim",
            booking_prefix="QPRINSEN",
            demo_room_id="quality-prinsen-meeting-room",
        ),
        Venue(
            id="quality-panorama",
            operator="Strawberry",
            name="Quality Hotel Panorama",
            location="Ivar Lykkes veg 1, Tiller",
            booking_prefix="QPANORAMA",
            demo_room_id="quality-panorama-meeting-room",
        ),
        Venue(
            id="quality-augustin",
            operator="Hoff Hotels",
            name="Quality Hotel Augustin",
            location="Kongens gate 26, Trondheim",
            booking_prefix="QAUGUSTIN",
            demo_room_id="quality-augustin-meeting-room",
        ),
        Venue(
            id="comfort-park",
            operator="Hoff Hotels",
            name="Comfort Hotel Park",
            location="Prinsensgate 4A, Trondheim",
            booking_prefix="CPARK",
            demo_room_id="comfort-park-meeting-room",
        ),
        Venue(
            id="comfort-trondheim",
            operator="Strawberry",
            name="Comfort Hotel Trondheim",
            location="Krambugata 11, Trondheim",
            booking_prefix="CTRONDHEIM",
            demo_room_id="comfort-trondheim-meeting-room",
        ),
        Venue(
            id="home-grand-olav",
            operator="Strawberry",
            name="Home Hotel Grand Olav",
            location="Kjøpmannsgata 48, Trondheim",
            booking_prefix="GRANDOLAV",
            demo_room_id="home-grand-olav-meeting-room",
        ),
        Venue(
            id="thon-nidaros",
            operator="Thon Hotels",
            name="Thon Hotel Nidaros",
            location="Søndre gate 22B, Trondheim",
            booking_prefix="THON",
            demo_room_id="thon-nidaros-meeting-room",
        ),
        Venue(
            id="olavshallen",
            operator="Olavshallen",
            name="Olavshallen",
            location="Kjøpmannsgata 48, Trondheim",
            booking_prefix="OLAVSHALLEN",
            demo_room_id="olavshallen-meeting-room",
        ),
        Venue(
            id="trondheim-spektrum",
            operator="Trondheim Spektrum",
            name="Trondheim Spektrum",
            location="Klostergata 90, Trondheim",
            booking_prefix="SPEKTRUM",
            demo_room_id="trondheim-spektrum-meeting-room",
        ),
        Venue(
            id="rockheim",
            operator="MiST",
            name="Rockheim",
            location="Brattørkaia 14, Trondheim",
            booking_prefix="ROCKHEIM",
            demo_room_id="rockheim-event-space",
        ),
        Venue(
            id="lager11",
            operator="Lager11",
            name="Lager11",
            location="Sluppenvegen 11, Trondheim",
            booking_prefix="LAGER11",
            demo_room_id="lager11-blackbox",
        ),
        Venue(
            id="salemhuset",
            operator="Salemhuset",
            name="Salemhuset",
            location="Prinsens gate 22B, Trondheim",
            booking_prefix="SALEM",
            demo_room_id="salemhuset-meeting-room",
        ),
        Venue(
            id="banksalen",
            operator="Banksalen",
            name="Banksalen",
            location="Kongens gate 4, Trondheim",
            booking_prefix="BANKSALEN",
            demo_room_id="banksalen-hall",
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
