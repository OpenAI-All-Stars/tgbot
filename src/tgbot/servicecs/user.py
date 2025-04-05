from aiogram import types

from tgbot.deps import db
from tgbot.entities.user import User
from tgbot.repositories import sql_users, sql_wallets
from tgbot.servicecs import wallet


async def registration(from_user: types.User) -> tuple[User, int]:
    registration_bonus = 100_000
    async with db.get().transaction():
        await sql_users.create(
            from_user.id,
            '',
            from_user.full_name,
            from_user.username or '',
        )
        await sql_wallets.create(
            from_user.id,
            0,
        )
        await wallet.add(from_user.id, registration_bonus)
    return User(
        user_id=from_user.id,
        full_name=from_user.full_name,
        username=from_user.username or '',
    ), registration_bonus
