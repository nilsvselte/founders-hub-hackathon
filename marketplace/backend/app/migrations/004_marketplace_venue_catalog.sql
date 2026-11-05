-- Existing preview venue keys and catalog display names serve different purposes.
ALTER TABLE marketplace_rooms ALTER COLUMN venue DROP NOT NULL;
ALTER TABLE marketplace_requests ALTER COLUMN venue DROP NOT NULL;

UPDATE marketplace_rooms
SET venue = NULL
WHERE owner_id IS NOT NULL OR id IN ('studio-demo-1', 'boardroom-demo-1');

UPDATE marketplace_rooms
SET city = 'Trondheim', venue_name = 'Kowork', kind = 'Meeting room',
    description = 'A shared meeting room at Kjøpmannsgata 40.',
    image_key = 'workshop'
WHERE id = 'kowork-meeting-room';

UPDATE marketplace_rooms
SET city = 'Trondheim', venue_name = 'Kowork', kind = 'Meeting room',
    description = 'A quiet room for a small conversation or focused work at Kjøpmannsgata 40.',
    image_key = 'huddle'
WHERE id = 'kowork-quiet-room';

UPDATE marketplace_requests AS request
SET venue = room.venue
FROM marketplace_rooms AS room
WHERE request.user_id IS NOT NULL AND request.room_id = room.id;

UPDATE marketplace_requests
SET venue = NULL
WHERE user_id IS NOT NULL AND room_id IS NULL;
