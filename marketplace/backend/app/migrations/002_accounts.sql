CREATE TABLE marketplace_users (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    role text NOT NULL DEFAULT 'renter' CHECK (role IN ('renter', 'host')),
    password_salt bytea NOT NULL CHECK (octet_length(password_salt) = 16),
    password_hash bytea NOT NULL CHECK (octet_length(password_hash) = 32),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE marketplace_sessions (
    token_hash bytea PRIMARY KEY CHECK (octet_length(token_hash) = 32),
    user_id uuid NOT NULL REFERENCES marketplace_users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL
);

CREATE INDEX marketplace_sessions_user_expiry ON marketplace_sessions (user_id, expires_at);
