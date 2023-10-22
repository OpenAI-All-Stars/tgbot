import sqlite3

import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from simple_settings import settings

from tgbot import deps
from tgbot.repositories import sql_users
from tgbot.servicecs import ai

HI_MSG = 'Добро пожаловать!'
CLOSE_MSG = 'Ходу нет!'
ALREADY_MSG = 'И снова добрый день!'

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    if message.text is None or message.from_user is None:
        return None

    if await sql_users.exists(message.from_user.id):
        await message.answer(ALREADY_MSG)
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(CLOSE_MSG)
        return

    code = parts[1]
    if code == settings.SECRET_PHRASE:
        await sql_users.create(
            message.from_user.id,
            message.chat.id,
            message.from_user.full_name,
            message.from_user.username or '',
        )
        await message.answer(HI_MSG)
    else:
        await message.answer(CLOSE_MSG)


@dp.message()
async def main_handler(message: types.Message) -> None:
    if message.text is None or message.from_user is None:
        return None

    user = await sql_users.get(message.from_user.id)
    if not user:
        return

    state = await ai.get_chat_state(user)
    if state.need_approve:
        if message.text.lower() in ('да', 'д', 'ok', 'ок', 'давай', 'yes', 'y'):
            answer = await state.execute()
        else:
            answer = await state.send(message.text)
    else:
        answer = await state.send(message.text)

    await message.answer(answer)


async def run() -> None:
    db = await aiosqlite.connect(settings.SQLITE_PATH)
    try:
        db.row_factory = sqlite3.Row
        deps.db.set(db)
        bot = Bot(settings.TG_TOKEN)
        await dp.start_polling(bot)
    finally:
        await db.close()
