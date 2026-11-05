ALTER TABLE marketplace_rooms
    ALTER COLUMN venue DROP NOT NULL,
    ADD COLUMN owner_id uuid REFERENCES marketplace_users(id),
    ADD COLUMN published boolean NOT NULL DEFAULT true,
    ADD COLUMN city text,
    ADD COLUMN venue_name text,
    ADD COLUMN kind text,
    ADD COLUMN description text,
    ADD COLUMN image_key text,
    ADD CONSTRAINT marketplace_rooms_complete_listing CHECK (
        num_nonnulls(city, venue_name, kind, description, image_key) IN (0, 5)
    );

ALTER TABLE marketplace_requests
    ALTER COLUMN venue DROP NOT NULL,
    ADD COLUMN user_id uuid REFERENCES marketplace_users(id),
    ADD COLUMN room_id text REFERENCES marketplace_rooms(id);

CREATE INDEX marketplace_requests_user_created
    ON marketplace_requests (user_id, created_at DESC);
CREATE INDEX marketplace_rooms_owner ON marketplace_rooms (owner_id);

UPDATE marketplace_rooms
SET city = 'Trondheim',
    venue_name = 'Kiln House',
    kind = 'Workshop',
    description = 'A long timber table and warm terracotta walls set the scene for group work and hands-on sessions.',
    image_key = 'workshop'
WHERE id = 'digs-demo-1';

UPDATE marketplace_rooms
SET city = 'Oslo',
    venue_name = 'Løkka House',
    kind = 'Meeting room',
    description = 'A quiet, light-filled corner for one-on-ones and small team conversations.',
    image_key = 'huddle'
WHERE id = 'digs-demo-2';

INSERT INTO marketplace_rooms (
    id, name, capacity, equipment, hourly_rate_ore, minimum_hourly_rate_ore,
    maximum_hourly_rate_ore, city, venue_name, kind, description, image_key
) VALUES
    (
        'studio-demo-1', 'Daylight Studio', 10, ARRAY['screen', 'whiteboard'],
        54000, 36000, 66000, 'Oslo', 'Studio Silo', 'Studio',
        'A bright studio with tall windows and a generous oak table for planning and creative work.',
        'studio'
    ),
    (
        'boardroom-demo-1', 'Harbour Boardroom', 12, ARRAY['screen', 'video conferencing'],
        72000, 50000, 85000, 'Bergen', 'Brygge Works', 'Boardroom',
        'A waterfront boardroom with panoramic views and space for presentations and larger groups.',
        'boardroom'
    );
