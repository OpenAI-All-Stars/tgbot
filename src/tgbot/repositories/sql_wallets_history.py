from tgbot.deps import db


INCREMENT_Q = """
INSERT INTO wallets_history (user_id, microdollars)
VALUES ($1, $2)
"""


async def add_change(user_id: int, value: int):
    await db.get().execute(
        INCREMENT_Q,
        user_id, value,
    )
