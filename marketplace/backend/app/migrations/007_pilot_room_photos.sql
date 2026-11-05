-- Use the venues' own meeting-room photos in the public catalog.
UPDATE marketplace_rooms
SET image_key = id
WHERE id IN ('brighten-meeting-room', 'kowork-meeting-room');
