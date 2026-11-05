UPDATE marketplace_rooms
SET venue_name = 'Mesh at Digs'
WHERE venue = 'digs' AND owner_id IS NULL
  AND id IN ('digs-demo-1', 'digs-demo-2');
