-- Kowork and Brighten room facts from their public websites, collected 2026-11-05.
-- Sources and what is stated versus inferred are listed in frontend/app/venue-facts.ts.
-- Neither venue publishes room prices, so hourly rates stay as proposed marketplace prices.

-- koteng.no: "Felles møterom for 8 til 12 personer", tenants only. The screen and soundbar are seen in Kowork's photo.
UPDATE marketplace_rooms
SET name = 'Shared meeting room',
    kind = 'Meeting room',
    capacity = 12,
    equipment = ARRAY['screen'],
    description = 'Kowork''s shared meeting room seats 8 to 12 around one long table, with a wall-mounted screen and soundbar. Today only Kowork tenants can book it, as part of their membership.'
WHERE id = 'kowork-meeting-room' AND owner_id IS NULL;

-- koteng.no: "Felles stillerom/samtalerom". Its size is not published, so capacity is an estimate.
UPDATE marketplace_rooms
SET name = 'Quiet room',
    kind = 'Quiet room',
    capacity = 2,
    equipment = ARRAY[]::text[],
    description = 'A shared quiet room for calls and one-to-one conversations at Kjøpmannsgata 40. Kowork doesn''t publish its size, so the capacity is an estimate.',
    image_key = 'kowork-venue'
WHERE id = 'kowork-quiet-room' AND owner_id IS NULL;

-- brighten.no lists "møterom" for members. Its photos show one glass-walled room with a round table and four chairs, and no screen.
UPDATE marketplace_rooms
SET name = 'Meeting room',
    kind = 'Meeting room',
    capacity = 4,
    equipment = ARRAY[]::text[],
    description = 'A glass-walled meeting room with a round table for four, inside Brighten''s coworking space in the 1914 Bakke Bydelshus on Bakklandet. Members book it ahead or use it when it''s free.'
WHERE id = 'brighten-meeting-room' AND owner_id IS NULL;

-- brighten.no: "Telefonpod" for calls and digital meetings. House rule: all calls happen here or in the meeting room.
UPDATE marketplace_rooms
SET name = 'Phone pod',
    kind = 'Phone pod',
    capacity = 1,
    equipment = ARRAY[]::text[],
    description = 'A one-person phone pod for calls and video meetings. At Brighten, all calls happen here or in the meeting room.',
    image_key = 'brighten-venue'
WHERE id = 'brighten-phone-pod' AND owner_id IS NULL;
