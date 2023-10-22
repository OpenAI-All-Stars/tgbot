CREATE TABLE IF NOT EXISTS users
(
    chat_id          INTEGER UNIQUE,
    user_id          INTEGER UNIQUE,
    full_name        TEXT,
    username         TEXT
);

CREATE TABLE IF NOT EXISTS chat_messages
(
    chat_id          INTEGER,
    body             TEXT,
    created_at       INTEGER
);
