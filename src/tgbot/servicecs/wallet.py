from tgbot.deps import db
from tgbot.repositories import sql_wallets, sql_wallets_history


async def add(user_id: int, value: int):
    async with db.get().transaction():
        await sql_wallets.add(
            user_id, value,
        )
        await sql_wallets_history.add_change(user_id, value)


async def spend(user_id: int, value: int):
    async with db.get().transaction():
        await sql_wallets.spend(
            user_id, value,
        )
        await sql_wallets_history.add_change(user_id, -value)
