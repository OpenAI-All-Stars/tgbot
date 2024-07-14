CREATE TABLE wallets
(
    user_id          INTEGER UNIQUE REFERENCES users(user_id),
    microdollars     INTEGER NOT NULL
);

CREATE TABLE wallets_history
(
    user_id          INTEGER REFERENCES users(user_id),
    microdollars     INTEGER NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);
