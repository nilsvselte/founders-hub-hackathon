CREATE TABLE marketplace_rooms (
    id text PRIMARY KEY,
    name text NOT NULL,
    capacity integer NOT NULL CHECK (capacity > 0),
    equipment text[] NOT NULL,
    hourly_rate_ore integer NOT NULL,
    minimum_hourly_rate_ore integer NOT NULL CHECK (minimum_hourly_rate_ore > 0),
    maximum_hourly_rate_ore integer NOT NULL,
    CHECK (hourly_rate_ore BETWEEN minimum_hourly_rate_ore AND maximum_hourly_rate_ore)
);

CREATE TABLE marketplace_openings (
    id uuid PRIMARY KEY,
    room_id text NOT NULL REFERENCES marketplace_rooms(id),
    source text NOT NULL,
    event_id text NOT NULL,
    block_id text NOT NULL,
    released_at timestamptz NOT NULL,
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL,
    UNIQUE (source, event_id),
    UNIQUE (source, room_id, block_id),
    CHECK (released_at <= start_at AND start_at < end_at)
);

CREATE TABLE marketplace_requests (
    id uuid PRIMARY KEY,
    earliest_start timestamptz NOT NULL,
    latest_end timestamptz NOT NULL,
    duration_minutes integer NOT NULL CHECK (duration_minutes > 0),
    party_size integer NOT NULL CHECK (party_size > 0),
    equipment text[] NOT NULL,
    max_price_ore integer NOT NULL CHECK (max_price_ore > 0),
    preferences text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (latest_end - earliest_start >= duration_minutes * interval '1 minute')
);

CREATE TABLE marketplace_offers (
    id uuid PRIMARY KEY,
    request_id uuid NOT NULL REFERENCES marketplace_requests(id),
    opening_id uuid NOT NULL REFERENCES marketplace_openings(id),
    room_id text NOT NULL REFERENCES marketplace_rooms(id),
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL,
    price_ore integer NOT NULL CHECK (price_ore > 0),
    expires_at timestamptz NOT NULL,
    match_reason text NOT NULL,
    match_provider text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    confirmed_at timestamptz,
    booking_reference text UNIQUE,
    CHECK (expires_at <= start_at AND start_at < end_at),
    CHECK ((confirmed_at IS NULL) = (booking_reference IS NULL))
);

CREATE INDEX marketplace_openings_room_end ON marketplace_openings (room_id, end_at);
CREATE INDEX marketplace_offers_request_expiry ON marketplace_offers (request_id, expires_at);
CREATE INDEX marketplace_offers_room_interval ON marketplace_offers (room_id, start_at, end_at);

INSERT INTO marketplace_rooms (
    id, name, capacity, equipment, hourly_rate_ore, minimum_hourly_rate_ore, maximum_hourly_rate_ore
) VALUES
    ('digs-demo-1', 'The Workshop', 8, ARRAY['screen', 'whiteboard', 'video conferencing'], 45000, 30000, 55000),
    ('digs-demo-2', 'The Huddle', 4, ARRAY['whiteboard'], 32000, 22000, 40000);
