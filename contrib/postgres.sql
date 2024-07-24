CREATE TABLE IF NOT EXISTS users
(
    user_id          BIGINT UNIQUE,
    full_name        TEXT,
    username         TEXT,
    invite_code      TEXT,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages
(
    user_id          BIGINT REFERENCES users(user_id),
    chat_id          BIGINT,
    body             TEXT,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wallets
(
    user_id          BIGINT UNIQUE REFERENCES users(user_id),
    microdollars     BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS wallets_history
(
    user_id          BIGINT REFERENCES users(user_id),
    microdollars     BIGINT NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);
