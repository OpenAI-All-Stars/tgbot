from aiogram import types

from tgbot.deps import db
from tgbot.entities.user import User
from tgbot.repositories import sql_users, sql_wallets
from tgbot.servicecs import wallet


async def registration(message: types.Message) -> tuple[User, int]:
    assert message.from_user
    registration_bonus = 100_000
    async with db.get().transaction():
        await sql_users.create(
            message.from_user.id,
            '',
            message.from_user.full_name,
            message.from_user.username or '',
        )
        await sql_wallets.create(
            message.from_user.id,
            0,
        )
        await wallet.add(message.from_user.id, registration_bonus)
    return User(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username or '',
    ), registration_bonus
