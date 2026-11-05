-- What a renter tells the marketplace agent: who they are (about), what rooms suit them (preferences),
-- and when the agent may suggest rooms or notify them (agent).
-- One row per account; a missing row means "use the defaults". Store a rough home point, never an exact address.
CREATE TABLE marketplace_user_preferences (
    user_id uuid PRIMARY KEY REFERENCES marketplace_users(id) ON DELETE CASCADE,

    -- About
    team_name text NOT NULL DEFAULT '' CHECK (length(team_name) <= 100),
    what_we_do text NOT NULL DEFAULT '' CHECK (length(what_we_do) <= 300),
    usual_party_size integer CHECK (usual_party_size BETWEEN 1 AND 100),
    home_area text NOT NULL DEFAULT '' CHECK (length(home_area) <= 100),
    home_lat double precision CHECK (home_lat BETWEEN -90 AND 90),
    home_lon double precision CHECK (home_lon BETWEEN -180 AND 180),
    meeting_types text[] NOT NULL DEFAULT '{}',
    agent_notes text NOT NULL DEFAULT '' CHECK (length(agent_notes) <= 1000),

    -- Preferences
    max_hourly_ore integer CHECK (max_hourly_ore BETWEEN 1 AND 10000000),
    room_kinds text[] NOT NULL DEFAULT '{}',
    equipment text[] NOT NULL DEFAULT '{}',
    preferred_venues text[] NOT NULL DEFAULT '{}',
    avoid_venues text[] NOT NULL DEFAULT '{}',
    max_travel_minutes integer CHECK (max_travel_minutes BETWEEN 1 AND 240),
    wishes text NOT NULL DEFAULT '' CHECK (length(wishes) <= 1000),

    -- Agent and notifications (channels are stored only; nothing is sent yet)
    allow_notifications boolean NOT NULL DEFAULT false,
    notification_channels text[] NOT NULL DEFAULT '{}'
        CHECK (notification_channels <@ ARRAY['in_app', 'email']::text[]),
    suggest_for_unroomed_meetings boolean NOT NULL DEFAULT true,
    suggestion_lead_days integer NOT NULL DEFAULT 3 CHECK (suggestion_lead_days BETWEEN 1 AND 14),
    min_attendees_to_suggest integer NOT NULL DEFAULT 2 CHECK (min_attendees_to_suggest BETWEEN 1 AND 100),
    skip_online_meetings boolean NOT NULL DEFAULT true,
    quiet_hours_start time,
    quiet_hours_end time,

    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((home_lat IS NULL) = (home_lon IS NULL)),
    CHECK ((quiet_hours_start IS NULL) = (quiet_hours_end IS NULL))
);
