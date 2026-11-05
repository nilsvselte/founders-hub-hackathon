-- Keep the demo IDs mapped to their original device venue.
UPDATE marketplace_rooms
SET city = 'Trondheim', venue_name = 'Digs'
WHERE id IN ('digs-demo-1', 'digs-demo-2')
  AND (city, venue_name) IS DISTINCT FROM ('Trondheim', 'Digs');
