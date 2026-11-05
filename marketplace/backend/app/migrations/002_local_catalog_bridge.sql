-- A development build used venue for display names before venue keys landed.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM marketplace_migrations WHERE name = '003_room_catalog.sql')
       AND NOT EXISTS (SELECT 1 FROM marketplace_migrations WHERE name = '002_venues.sql')
       AND EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema = current_schema() AND table_name = 'marketplace_rooms' AND column_name = 'venue'
       )
       AND NOT EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema = current_schema() AND table_name = 'marketplace_rooms' AND column_name = 'venue_name'
       ) THEN
        ALTER TABLE marketplace_rooms RENAME COLUMN venue TO venue_name;
    END IF;
END
$$;
