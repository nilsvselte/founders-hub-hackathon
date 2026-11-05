-- Continue the public-source checks from 014. See marketplace/VENUE_RESEARCH.md for
-- operator booking pages, photo sources, and the four venues that remain drafts.
-- These are demo listings: public-source verification is not operator onboarding.
-- Retain venue-photo labels and demo rates/capacities for generic sample rooms.

-- Regus's own Powerhouse page confirms the operator and address. Keep the internal
-- key, room IDs, and booking prefix so existing requests and references still work.
UPDATE marketplace_rooms
SET venue_name = 'Regus Powerhouse'
WHERE owner_id IS NULL AND venue = 'spaces-powerhouse' AND venue_name = 'Spaces Powerhouse';

UPDATE marketplace_rooms
SET description = 'A meeting room at Regus Powerhouse, Brattørkaia 17A.'
WHERE owner_id IS NULL AND id = 'spaces-powerhouse-meeting-room'
  AND description = 'A meeting room at Spaces in Powerhouse Brattørkaia, Brattørkaia 17A.';

UPDATE marketplace_rooms
SET description = 'A boardroom at Regus Powerhouse, Brattørkaia 17A.'
WHERE owner_id IS NULL AND id = 'spaces-powerhouse-boardroom'
  AND description = 'A boardroom for up to 12 people at Spaces in Powerhouse Brattørkaia.';

-- The operator now lists rooms 610 and Frisøren. Remove the old single-room claim.
UPDATE marketplace_rooms
SET description = 'A meeting room at Home Hotel Grand Olav, in the same building as Olavshallen. The hotel lists rooms 610 and Frisøren.'
WHERE owner_id IS NULL AND id = 'home-grand-olav-meeting-room'
  AND description = 'The hotel''s single meeting room seats 12, in the same building as Olavshallen.';

-- Official Clarion pages disagree on the venue-wide room count; omit that total.
UPDATE marketplace_rooms
SET description = 'A meeting room at Clarion Hotel Trondheim on Brattørkaia.'
WHERE owner_id IS NULL AND id = 'clarion-trondheim-meeting-room'
  AND description = 'One of 18 meeting rooms at Clarion Hotel Trondheim on Brattørkaia.';

UPDATE marketplace_rooms
SET published = true
WHERE owner_id IS NULL AND image_key = venue || '-venue' AND venue IN (
    'workwork', 'spaces-powerhouse', 'clarion-trondheim', 'britannia',
    'quality-prinsen', 'quality-panorama', 'comfort-trondheim', 'home-grand-olav'
);
