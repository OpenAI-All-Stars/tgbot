CREATE TABLE users
(
    chat_id          INTEGER UNIQUE,
    user_id          INTEGER UNIQUE,
    full_name        TEXT,
    username         TEXT,
    invite_code      TEXT
);

CREATE TABLE chat_messages
(
    chat_id          INTEGER,
    body             TEXT,
    created_at       INTEGER
);
