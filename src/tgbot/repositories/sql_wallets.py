from tgbot.deps import db


INCREMENT_Q = """
UPDATE wallets
SET microdollars = wallets.microdollars + $2
WHERE user_id = $1
"""


async def create(user_id: int, value: int):
    await db.get().execute(
        """
        INSERT INTO wallets (user_id, microdollars)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO NOTHING
        """,
        user_id, value,
    )


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
    value = await db.get().fetchval(
        """
        SELECT microdollars
        FROM wallets
        WHERE user_id = $1
        """,
        user_id,
    )
    if value is None:
        return 0
    return value
