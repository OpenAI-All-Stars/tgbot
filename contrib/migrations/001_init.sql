CREATE TABLE users
(
    chat_id          INTEGER UNIQUE,
    user_id          INTEGER UNIQUE,
    full_name        TEXT,
    username         TEXT,
    invite_code      TEXT,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_messages
(
    chat_id          INTEGER,
    body             TEXT,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);
