import asyncio
from asyncio import Event
import io

from aiogram import F, Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import BotCommand, BufferedInputFile, LabeledPrice
from asyncpg import UniqueViolationError
from simple_settings import settings

from tgbot.deps import telemetry, db
from tgbot.repositories import http_openai, sql_chat_messages, sql_users, sql_wallets
from tgbot.servicecs import ai, wallet
from tgbot.utils import get_sign, tick_iterator

HI_MSG = 'Добро пожаловать!'
ALREADY_MSG = 'И снова добрый день!'

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if message.text is None or message.from_user is None:
        return

    if await sql_users.exists(message.from_user.id):
        await message.answer(ALREADY_MSG)
        return

    try:
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
    except UniqueViolationError:
        pass
    await message.answer(HI_MSG)


@dp.message(Command('clean'))
async def cmd_clean(message: types.Message):
    await sql_chat_messages.clean(message.chat.id)
    await message.answer('Контекст очищен')


@dp.message(Command('balance'))
async def cmd_balance(message: types.Message):
    assert message.from_user
    microdollars = await sql_wallets.get(message.from_user.id)
    await message.answer('Баланс: {}${:.2f}'.format(get_sign(microdollars), abs(microdollars / 1_000_000)))


@dp.message(Command('buy_stars'))
async def cmd_buy(message: types.Message, command: CommandObject):
    assert message.from_user

    if command.args is None:
        amount = 1
    else:
        if (
            not command.args.isdigit()
            or not 1 <= int(command.args) <= 2500
        ):
            await message.answer('Введите сумму в формате /buy_stars ЧИСЛО, где ЧИСЛО от 1 до 2500.')
            return
        amount = int(command.args)

    await message.answer_invoice(
        title='Пополнение баланса',
        description='На {} ⭐'.format(amount),
        provider_token='',
        currency='XTR',
        prices=[LabeledPrice(label='XTR', amount=amount)],
        payload=str(message.from_user.id),
    )


@dp.pre_checkout_query(lambda query: True)
async def pre_checkout_query_handler(pre_checkout_q: types.PreCheckoutQuery):
    await pre_checkout_q.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    assert message.successful_payment
    payment_info = message.successful_payment
    await wallet.add(int(payment_info.invoice_payload), message.successful_payment.total_amount * 13_000)
    await message.answer(
        'Платеж на сумму ${:.2f} прошел успешно!\n\nАйди транзакции:\n`{}`'.format(
            message.successful_payment.total_amount * 13_000 / 1_000_000,
            message.successful_payment.telegram_payment_charge_id,
        ),
    )


@dp.message()
async def main_handler(message: types.Message):
    if message.from_user is None:
        return None

    stop = Event()
    try:
        asyncio.create_task(send_typing(message, stop))
        await send_answer(message)
    finally:
        stop.set()


async def send_typing(message: types.Message, stop: Event):
    assert message.chat
    assert message.bot
    async for _ in tick_iterator(5):
        if stop.is_set():
            break
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)


async def send_answer(message: types.Message):
    assert message.from_user
    assert message.bot
    user, balance = await asyncio.gather(
        sql_users.get(message.from_user.id),
        sql_wallets.get(message.from_user.id)
    )
    if not user:
        await message.answer('Ошибка. Вызовите команду /start.')
        return
    if balance <= 0:
        await message.answer((
            'Недостаточно средств на счету. '
            'Для продолжения работы с ботом вам необходимо пополнить баланс.'
        ))
        return

    telemetry.get().incr('messages')

    if message.voice:
        file_params = await message.bot.get_file(message.voice.file_id)
        assert file_params.file_path
        file_data = io.BytesIO()
        try:
            await message.bot.download_file(file_params.file_path, file_data)
            file_data.name = 'voice.ogg'
            requeset_text = await http_openai.audio2text(file_data)
        finally:
            file_data.close()
    elif message.text:
        requeset_text = message.text
    else:
        return

    state = await ai.get_chat_state(message)
    answer = await state.send(requeset_text)
    if isinstance(answer, bytes):
        await message.bot.send_photo(
            message.chat.id,
            BufferedInputFile(answer, 'answer.jpg'),
        )
    elif isinstance(answer, str):
        await message.answer(answer)


async def run() -> None:
    bot = Bot(
        settings.TG_TOKEN,
        parse_mode=ParseMode.MARKDOWN,
        session=AiohttpSession(
            api=TelegramAPIServer.from_base(settings.TELEGRAM_BASE_URL),
        ),
    )
    await bot.set_my_commands(commands=[
        BotCommand(command='/buy_stars', description='Пополнить баланс звёздами'),
        BotCommand(command='/balance', description='Показать баланс'),
        BotCommand(command='/clean', description='Очистить контекст'),
    ])
    await dp.start_polling(bot, handle_signals=False)
