CREATE TABLE IF NOT EXISTS users
(
    user_id          INTEGER UNIQUE,
    full_name        TEXT,
    username         TEXT,
    invite_code      TEXT
);

CREATE TABLE IF NOT EXISTS chat_messages
(
    user_id          INTEGER REFERENCES users(user_id),
    chat_id          INTEGER,
    body             TEXT,
    created_at       INTEGER
);

CREATE TABLE IF NOT EXISTS wallets
(
    user_id          INTEGER UNIQUE REFERENCES users(user_id),
    microdollars     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS wallets_history
(
    user_id          INTEGER REFERENCES users(user_id),
    microdollars     INTEGER NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);
