CREATE TABLE wallets
(
    user_id          BIGINT UNIQUE REFERENCES users(user_id),
    microdollars     BIGINT NOT NULL
);

CREATE TABLE wallets_history
(
    user_id          BIGINT REFERENCES users(user_id),
    microdollars     BIGINT NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);
