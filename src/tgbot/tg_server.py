import asyncio
from asyncio import Event
import io

from aiogram import F, Dispatcher, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import BotCommand, BufferedInputFile, LabeledPrice, InlineKeyboardButton
from openai.types.completion_usage import CompletionUsage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from asyncpg import UniqueViolationError
from simple_settings import settings

from tgbot import price, sentry_aiogram_integration
from tgbot.deps import telemetry, db, tg_bot
from tgbot.repositories import http_openai, sql_chat_messages, sql_users, sql_wallets
from tgbot.servicecs import ai, wallet
from tgbot.utils import get_sign, tick_iterator

HI_MSG = 'Добро пожаловать!'
ALREADY_MSG = 'И снова добрый день!'

dp = Dispatcher()
sentry_aiogram_integration.init(dp)


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


@dp.message(Command('pay'))
async def cmd_pay(message: types.Message):
    assert message.from_user
    microdollars = await sql_wallets.get(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text='Пополнить баланс картой', url='{}{}'.format(
            settings.PAYMENT_URL_PREFIX,
            message.from_user.id,
        ),
    ))
    builder.row(InlineKeyboardButton(
        text='Пополнить баланс звёздами', callback_data='pay_stars',
    ))
    builder.row(InlineKeyboardButton(
        text='Цены', callback_data='price',
    ))
    await message.answer(
        'Баланс: {}${:.2f}'.format(get_sign(microdollars), abs(microdollars / 1_000_000)),
        reply_markup=builder.as_markup(),
    )


@dp.callback_query(F.data == 'price')
async def callback_price(callback: types.CallbackQuery):
    if not isinstance(callback.message, types.Message):
        return
    await callback.message.answer((
        'Цены:\n'
        '- Промт (ваш запрос боту): *${prompt_token:.3f}* за тысячу токенов\\*.\n'
        '- Ответ: *${completion_token:.3f}* за тысячу токенов\\*.\n'
        '- Генерация равностороннего изображения: *${image_square:.3f}*.\n'
        '- Генерация изображения альбомной/портретной развертки: *${image_other:.3f}*.\n'
        '- Распознование голосового сообщения: *${audio2text:.3f}* за 10 минут.\n'
        '\n'
        '\\*Токены могут включать:\n'
        '1. Слова целиком. Например, слово "привет" будет одним токеном.\n'
        '2. Части слов, в зависимости от языка и его сложности. Например, '
        'длинное сложное слово может быть разложено на несколько токенов.\n'
        '3. Пробелы и знаки препинания. Пробелы и пунктуация также считаются токенами.'
        ''.format(
            prompt_token=price.chatgpt_completion(CompletionUsage(
                completion_tokens=0,
                prompt_tokens=1_000,
                total_tokens=1_000,
            )) / 1_000_000,
            completion_token=price.chatgpt_completion(CompletionUsage(
                completion_tokens=1_000,
                prompt_tokens=0,
                total_tokens=1_000,
            )) / 1_000_000,
            image_square=price.generate_image('1024x1024') / 1_000_000,
            image_other=price.generate_image('1792x1024') / 1_000_000,
            audio2text=price.audio2text(10*60) / 1_000_000,
        )
    ))


@dp.callback_query(F.data == 'pay_stars')
async def callback_pay_stars(callback: types.CallbackQuery):
    if not isinstance(callback.message, types.Message):
        return
    assert callback.message.from_user
    amount = 50
    await callback.message.answer_invoice(
        title='Пополнение баланса',
        description='/pay_stars ЧИСЛО - пополнение на другую сумму',
        provider_token='',
        currency='XTR',
        prices=[LabeledPrice(label='XTR', amount=amount)],
        payload=str(callback.message.from_user.id),
    )


@dp.message(Command('pay_stars'))
async def cmd_pay_stars(message: types.Message, command: CommandObject):
    assert message.from_user

    if command.args is None:
        amount = 50
    else:
        if (
            not command.args.isdigit()
            or not 1 <= int(command.args) <= 2500
        ):
            await message.answer('Введите сумму в формате /pay_stars ЧИСЛО, где ЧИСЛО от 1 до 2500.')
            return
        amount = int(command.args)

    await message.answer_invoice(
        title='Пополнение баланса',
        description='/pay_stars ЧИСЛО - пополнение на другую сумму',
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
    telemetry.get().incr('messages')
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
    async for _ in tick_iterator(5):
        if stop.is_set():
            break
        await tg_bot.get().send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)


async def send_answer(message: types.Message):
    assert message.from_user
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

    if message.voice:
        file_params = await tg_bot.get().get_file(message.voice.file_id)
        assert file_params.file_path
        file_data = io.BytesIO()
        try:
            await tg_bot.get().download_file(file_params.file_path, file_data)
            file_data.name = 'voice.ogg'
            requeset_text = await http_openai.audio2text(file_data)
        finally:
            file_data.close()
        await wallet.spend(message.from_user.id, price.audio2text(message.voice.duration))
    elif message.text:
        requeset_text = message.text
    else:
        return

    state = await ai.get_chat_state(message)
    answer = await state.send(requeset_text)
    if isinstance(answer, bytes):
        await message.answer_photo(
            BufferedInputFile(answer, 'answer.jpg'),
        )
    elif isinstance(answer, str):
        if len(answer) > 4096:
            await message.answer_document(
                BufferedInputFile(answer.encode(), filename='answer.txt'),
            )
        else:
            try:
                await message.answer(answer)
            except TelegramBadRequest as e:
                if 'can\'t parse entities' in str(e):
                    await message.answer(answer, parse_mode=ParseMode.HTML)
                else:
                    raise


async def run() -> None:
    await tg_bot.get().set_my_commands(commands=[
        BotCommand(command='/pay', description='Пополнить баланс'),
        BotCommand(command='/clean', description='Очистить контекст'),
    ])
    await dp.start_polling(tg_bot.get(), handle_signals=False)
