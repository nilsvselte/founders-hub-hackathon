-- Use Brighten's own photo of its glass-walled meeting room (from brighten.no) instead of the catalog shot.
-- brighten.no has no photo of the phone pod, so it keeps none.
UPDATE marketplace_rooms SET photo = 'brighten-meeting-room.webp' WHERE id = 'brighten-meeting-room';
