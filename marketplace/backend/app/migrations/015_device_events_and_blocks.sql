CREATE TABLE marketplace_device_blocks (
    id uuid PRIMARY KEY,
    room_id text NOT NULL REFERENCES marketplace_rooms(id),
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL,
    opening_id uuid UNIQUE REFERENCES marketplace_openings(id),
    CHECK (start_at < end_at)
);

CREATE INDEX marketplace_device_blocks_room_interval
    ON marketplace_device_blocks (room_id, start_at, end_at);

CREATE TABLE marketplace_device_events (
    source text NOT NULL,
    event_id text NOT NULL,
    room_id text NOT NULL REFERENCES marketplace_rooms(id),
    kind text NOT NULL CHECK (kind IN ('occupancy_changed', 'release_requested')),
    opening_id uuid REFERENCES marketplace_openings(id),
    PRIMARY KEY (source, event_id)
);

CREATE TABLE marketplace_room_occupancy (
    room_id text PRIMARY KEY REFERENCES marketplace_rooms(id),
    occupied boolean NOT NULL,
    changed_at timestamptz NOT NULL,
    source text NOT NULL,
    event_id text NOT NULL,
    FOREIGN KEY (source, event_id) REFERENCES marketplace_device_events(source, event_id)
);
