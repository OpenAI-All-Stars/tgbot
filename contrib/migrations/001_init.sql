CREATE TABLE users
(
    chat_id          BIGINT UNIQUE,
    user_id          BIGINT UNIQUE,
    full_name        TEXT,
    username         TEXT,
    invite_code      TEXT,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_messages
(
    chat_id          BIGINT,
    body             TEXT,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);
