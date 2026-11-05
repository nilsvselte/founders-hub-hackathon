-- Brighten, Bakke Bydelshus, Nordre Berggate 2: a coworking space on Bakklandet in Trondheim.
-- brighten.no says only that members can book the meeting room and the phone pod ahead or use them when free.
-- It lists no room names, capacities, equipment, or prices, so every value below is a placeholder until Brighten confirms them.
INSERT INTO marketplace_rooms (
    id, venue, name, capacity, equipment, hourly_rate_ore, minimum_hourly_rate_ore, maximum_hourly_rate_ore
) VALUES
    ('brighten-meeting-room', 'brighten', 'Meeting room', 6, ARRAY['screen', 'video conferencing'], 40000, 25000, 50000),
    ('brighten-phone-pod', 'brighten', 'Phone pod', 1, ARRAY[]::text[], 10000, 7500, 15000);
