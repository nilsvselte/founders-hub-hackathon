-- Room photos served by the frontend from public/rooms/. Rooms without a photo show none.
ALTER TABLE marketplace_rooms ADD COLUMN photo text;

UPDATE marketplace_rooms SET photo = 'workshop.webp' WHERE id = 'digs-demo-1';
UPDATE marketplace_rooms SET photo = 'huddle.webp' WHERE id = 'digs-demo-2';
UPDATE marketplace_rooms SET photo = 'boardroom.webp' WHERE id = 'kowork-meeting-room';
UPDATE marketplace_rooms SET photo = 'studio.webp' WHERE id = 'brighten-meeting-room';
