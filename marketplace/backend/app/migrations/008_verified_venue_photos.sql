UPDATE marketplace_rooms
SET published = false
WHERE owner_id IS NULL AND id IN ('studio-demo-1', 'boardroom-demo-1');

UPDATE marketplace_rooms
SET image_key = 'none'
WHERE image_key IN ('studio', 'workshop', 'huddle', 'boardroom');

UPDATE marketplace_rooms
SET photo = NULL
WHERE photo IN ('studio.webp', 'workshop.webp', 'huddle.webp', 'boardroom.webp');

-- Names, capacities and amenities follow Mesh's official Trondheim room listings.
UPDATE marketplace_rooms
SET name = 'Driv',
    kind = 'Meeting room',
    capacity = 14,
    equipment = ARRAY['video conferencing'],
    description = 'Room 507 has a large table for up to 14 people and presentation technology for hybrid meetings.',
    image_key = 'digs-driv',
    photo = 'digs-driv.webp'
WHERE id = 'digs-demo-1' AND venue = 'digs' AND owner_id IS NULL;

UPDATE marketplace_rooms
SET name = 'Gnist',
    kind = 'Meeting room',
    capacity = 4,
    equipment = ARRAY['screen', 'video conferencing'],
    description = 'Room 502 seats four and has a digital board for presentations and video calls.',
    image_key = 'digs-gnist-spark',
    photo = 'digs-gnist-spark.webp'
WHERE id = 'digs-demo-2' AND venue = 'digs' AND owner_id IS NULL;
