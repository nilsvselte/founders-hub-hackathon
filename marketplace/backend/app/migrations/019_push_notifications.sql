CREATE TABLE marketplace_push_subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES marketplace_users(id) ON DELETE CASCADE,
    endpoint text NOT NULL UNIQUE,
    p256dh text NOT NULL,
    auth text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX marketplace_push_subscriptions_user ON marketplace_push_subscriptions (user_id);

CREATE TABLE marketplace_notification_settings (
    user_id uuid PRIMARY KEY REFERENCES marketplace_users(id) ON DELETE CASCADE,
    room_booked boolean NOT NULL DEFAULT true,
    occupied_unbooked boolean NOT NULL DEFAULT true,
    booked_empty boolean NOT NULL DEFAULT true,
    offer_ready boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- One row per notification that must not repeat, e.g. 'booked_empty:<offer id>'
-- or 'occupied_unbooked:<room id>' (resent after 30 minutes).
CREATE TABLE marketplace_notification_log (
    key text PRIMARY KEY,
    sent_at timestamptz NOT NULL DEFAULT now()
);
