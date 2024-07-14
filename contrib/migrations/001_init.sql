CREATE TABLE IF NOT EXISTS users
(
    chat_id          INTEGER UNIQUE,
    user_id          INTEGER UNIQUE,
    full_name        TEXT,
    username         TEXT,
    invite_code      TEXT,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages
(
    chat_id          INTEGER,
    body             TEXT,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);
