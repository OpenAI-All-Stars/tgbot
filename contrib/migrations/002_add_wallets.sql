CREATE TABLE IF NOT EXISTS wallets
(
    user_id          INTEGER UNIQUE NOT NULL,
    microdollars     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS wallets_history
(
    user_id          INTEGER REFERENCES users(user_id),
    microdollars     INTEGER NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);
