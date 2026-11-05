CREATE TABLE marketplace_agent_tokens (
    user_id uuid PRIMARY KEY REFERENCES marketplace_users(id) ON DELETE CASCADE,
    token_hash bytea NOT NULL UNIQUE CHECK (octet_length(token_hash) = 32)
);
