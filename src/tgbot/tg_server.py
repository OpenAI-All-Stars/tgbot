import asyncio
from asyncio import Event

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import CommandStart
from simple_settings import settings

from tgbot.repositories import sql_users
from tgbot.servicecs import ai
from tgbot.utils import tick_iterator

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

    stop = Event()
    asyncio.create_task(send_typing(message, stop))
    try:
        await send_answer(message)
    finally:
        stop.set()


async def send_typing(message: types.Message, stop: Event) -> None:
    assert message.chat
    assert message.bot
    async for _ in tick_iterator(5):
        if stop.is_set():
            break
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)


async def send_answer(message: types.Message) -> None:
    assert message.from_user
    assert message.text
    user = await sql_users.get(message.from_user.id)
    if not user:
        return

    state = await ai.get_chat_state(user)
    answer = await state.send(message.text)

    await message.answer(answer)


async def run() -> None:
    bot = Bot(settings.TG_TOKEN, parse_mode=ParseMode.MARKDOWN)
    await dp.start_polling(bot)
