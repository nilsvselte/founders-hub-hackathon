-- Scope rooms and standby requests to a venue. Existing rows belong to Digs.
ALTER TABLE marketplace_rooms ADD COLUMN venue text NOT NULL DEFAULT 'digs';
ALTER TABLE marketplace_rooms ALTER COLUMN venue DROP DEFAULT;
ALTER TABLE marketplace_requests ADD COLUMN venue text NOT NULL DEFAULT 'digs';
ALTER TABLE marketplace_requests ALTER COLUMN venue DROP DEFAULT;

-- Kowork, Kjøpmannsgata 40: a shared meeting room for 8 to 12 people and a quiet room.
-- Capacities come from koteng.no. Equipment and prices are placeholders until Kowork confirms them.
INSERT INTO marketplace_rooms (
    id, venue, name, capacity, equipment, hourly_rate_ore, minimum_hourly_rate_ore, maximum_hourly_rate_ore
) VALUES
    ('kowork-meeting-room', 'kowork', 'Shared meeting room', 12, ARRAY['screen', 'whiteboard'], 50000, 35000, 60000),
    ('kowork-quiet-room', 'kowork', 'Quiet room', 2, ARRAY[]::text[], 15000, 10000, 20000);
