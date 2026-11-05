-- Venue photos for the 011 Trondheim catalog. Each photo is the venue's own, taken from the venue's or its
-- hotel chain's website (or a listing of the building where the venue has no site of its own).
-- Room names are generic, so each photo is labelled as a venue photo rather than a photo of that exact room.
-- Only seeded rows that still have no photo are changed; host-edited rooms and publish state are left alone.
-- workwork: Work-Work's bar and shared office (work-work.no)
-- bargaflyt: BargaFlyt's coworking floor at Olav Tryggvasons gate 40 (office-hub.com building listing)
-- olo: OLO fellesverksted's workshop (olo.no)
-- spaces-powerhouse: Powerhouse Brattørkaia, the building Spaces and Regus operate in (regus.com)
-- clarion-trondheim: Clarion Hotel & Congress Trondheim's facade (strawberry.no)
-- radisson-royal-garden: the Olav Tryggvason 1 meeting room (radissonhotels.com)
-- radisson-airport: a hotel meeting room (radissonhotels.com)
-- britannia: Britannia Hotel's facade (britannia.no)
-- comfort-park: Comfort Hotel Park's facade (strawberry.no)
-- comfort-trondheim: Comfort Hotel Trondheim's facade (strawberry.no)
-- quality-panorama: Quality Hotel Panorama's facade (strawberry.no)
-- quality-prinsen: Quality Hotel Prinsen's entrance (strawberry.no)
-- quality-augustin: Quality Hotel Augustin's facade (strawberry.no)
-- home-grand-olav: Home Hotel Grand Olav's lounge (the hotel's MeetingPackage page linked from strawberry.no)
-- scandic-bakklandet: the Brinken meeting room (scandichotels.com)
-- scandic-lerkendal: a conference room (scandichotels.com)
-- scandic-nidelven: the Trondhjemssalen conference hall (scandichotels.com)
-- scandic-solsiden: a meeting room (scandichotels.com)
-- scandic-hell: the Langøra meeting room (scandichotels.com)
-- thon-nidaros: Thon Hotel Nidaros's lobby (thonhotels.no)
-- lager11: an event in Lager11's hall (lager11.no)
-- olavshallen: the main concert hall (olavshallen.no)
-- rockheim: Rockheim's conference room (rockheim.no)
-- salemhuset: Salemhuset's meeting room (salemhuset.no)
-- trondheim-spektrum: a Trondheim Spektrum meeting room (trondheimspektrum.no)
-- banksalen: Banksalen's meeting room (banksalen.no)
UPDATE marketplace_rooms
SET image_key = venue || '-venue', photo = venue || '-venue.webp'
WHERE owner_id IS NULL AND image_key = 'none' AND venue IN (
    'workwork', 'bargaflyt', 'olo', 'spaces-powerhouse',
    'clarion-trondheim', 'radisson-royal-garden', 'radisson-airport', 'britannia',
    'comfort-park', 'comfort-trondheim', 'quality-panorama', 'quality-prinsen',
    'quality-augustin', 'home-grand-olav', 'scandic-bakklandet', 'scandic-lerkendal',
    'scandic-nidelven', 'scandic-solsiden', 'scandic-hell', 'thon-nidaros',
    'lager11', 'olavshallen', 'rockheim', 'salemhuset',
    'trondheim-spektrum', 'banksalen'
);
