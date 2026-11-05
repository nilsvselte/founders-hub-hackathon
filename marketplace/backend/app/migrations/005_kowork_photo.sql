-- Use Kowork's own meeting room photo from koteng.no instead of the stock boardroom photo.
UPDATE marketplace_rooms SET photo = 'kowork-meeting-room.webp' WHERE id = 'kowork-meeting-room';
