from tgbot.deps import db


INCREMENT_Q = """
INSERT INTO wallets (user_id, microdollars)
VALUES ($1, $2)
ON CONFLICT (user_id) DO UPDATE
SET microdollars = wallets.microdollars + EXCLUDED.microdollars
"""


async def add(user_id: int, value: int):
    await db.get().execute(
        INCREMENT_Q,
        user_id, value,
    )


async def spend(user_id: int, value: int):
    await db.get().execute(
        INCREMENT_Q,
        user_id, -value,
    )


async def get(user_id: int) -> int:
    return await db.get().fetchval(
        """
        SELECT microdollars
        FROM wallets
        WHERE user_id = $1
        """,
        user_id,
    )
