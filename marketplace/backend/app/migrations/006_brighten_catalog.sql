UPDATE marketplace_rooms AS room
SET city = 'Trondheim',
    venue_name = 'Brighten',
    kind = 'Meeting room',
    description = catalog.description,
    image_key = catalog.image_key
FROM (VALUES
    ('brighten-meeting-room', 'A meeting room at Brighten, a coworking space in Bakke Bydelshus on Bakklandet.', 'workshop'),
    ('brighten-phone-pod', 'A private phone pod at Brighten in Bakke Bydelshus on Bakklandet.', 'huddle')
) AS catalog(id, description, image_key)
WHERE room.id = catalog.id
  AND room.venue = 'brighten'
  AND (room.city, room.venue_name, room.kind, room.description, room.image_key) IS DISTINCT FROM
      ('Trondheim', 'Brighten', 'Meeting room', catalog.description, catalog.image_key);
