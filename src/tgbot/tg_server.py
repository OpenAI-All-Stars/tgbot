import asyncio
from asyncio import Event
import io
from pathlib import Path

from aiogram import F, Dispatcher, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import BotCommand, BufferedInputFile, LabeledPrice, InlineKeyboardButton
from openai.types.completion_usage import CompletionUsage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from simple_settings import settings

from tgbot import price, sentry_aiogram_integration
from tgbot.deps import telemetry, tg_bot
from tgbot.repositories import http_openai, sql_chat_messages, sql_users, sql_wallets
from tgbot.servicecs import ai, wallet
from tgbot.servicecs.user import registration
from tgbot.utils import convert_pdf_to_text, get_sign, tick_iterator, skip_message


ALREADY_MSG = 'И снова добрый день!'
NEED_PAY_MSG = (
    'Недостаточно средств на счету. '
    'Для продолжения работы с ботом вам необходимо пополнить баланс.'
)

dp = Dispatcher()
sentry_aiogram_integration.init(dp)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if message.chat.type != 'private':
        return

    telemetry.get().incr('messages.start')
    if message.text is None or message.from_user is None:
        return

    if await sql_users.exists(message.from_user.id):
        await message.answer(ALREADY_MSG)
        return

    await registration(message.from_user)
    await message.answer('Добро пожаловать! За регистрацию вам зачислено $0.1!')


@dp.message(Command('clean'))
async def cmd_clean(message: types.Message):
    telemetry.get().incr('messages.clean')
    await sql_chat_messages.clean(message.chat.id)
    await message.answer('Контекст очищен')


@dp.message(Command('pay'))
async def cmd_pay(message: types.Message):
    if message.chat.type != 'private':
        return
    telemetry.get().incr('messages.pay')
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
    telemetry.get().incr('messages.price')
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
    assert callback.from_user
    amount = 50
    await callback.message.answer_invoice(
        title='Пополнение баланса',
        description='/pay_stars ЧИСЛО - пополнение на другую сумму',
        provider_token='',
        currency='XTR',
        prices=[LabeledPrice(label='XTR', amount=amount)],
        payload=str(callback.from_user.id),
    )


@dp.message(Command('pay_stars'))
async def cmd_pay_stars(message: types.Message, command: CommandObject):
    if message.chat.type != 'private':
        return
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


@dp.message(F.document)
async def handle_document(message: types.Message):
    if await skip_message(message):
        return

    assert message.from_user
    assert message.document
    assert message.document.file_name
    telemetry.get().incr('messages.document')
    is_group = message.chat.type in ['group', 'supergroup']
    send_response = message.reply if is_group else message.answer
    balance = await sql_wallets.get(message.from_user.id)
    if balance <= 0:
        await send_response(NEED_PAY_MSG)
        return
    file = await tg_bot.get().get_file(message.document.file_id)
    if file.file_path is None:
        return
    data = io.BytesIO()
    await tg_bot.get().download_file(file.file_path, data)
    match Path(message.document.file_name).suffix.lower():
        case '.txt':
            text = data.read().decode()
        case '.pdf':
            text = await convert_pdf_to_text(data)
        case _:
            await send_response('Не удалось прочесть файл. Доступные форматы: txt, pdf.')
            return
    await ai.append_text(message.from_user.id, text)
    await send_response('Файл прочитан.')


@dp.inline_query.register
async def inline_handler(inline_query: types.InlineQuery):
    if not (inline_query.query and inline_query.query[-1] in '.?'):
        item = types.InlineQueryResultArticle(
            id='1',
            title='Поставь . или ? в конце и я подготовлю ответ',
            input_message_content=types.InputTextMessageContent(message_text='?'),
        )
        await tg_bot.get().answer_inline_query(inline_query.id, results=[item], cache_time=1)
        return

    user, balance = await asyncio.gather(
        sql_users.get(inline_query.from_user.id),
        sql_wallets.get(inline_query.from_user.id)
    )
    if not user:
        user, balance = await registration(inline_query.from_user)
    if balance <= 0:
        item = types.InlineQueryResultArticle(
            id='1',
            title='Недостаточно средств на счету',
            input_message_content=types.InputTextMessageContent(message_text=NEED_PAY_MSG),
        )
        await tg_bot.get().answer_inline_query(inline_query.id, results=[item], cache_time=1)
        return

    answer = await ai.send_only_text(inline_query.from_user.id, inline_query.query.strip())
    if not answer:
        return

    input_content = types.InputTextMessageContent(message_text=answer)
    item = types.InlineQueryResultArticle(
        id='1',
        title='Отправить',
        input_message_content=input_content,
    )
    await tg_bot.get().answer_inline_query(inline_query.id, results=[item], cache_time=1)


@dp.message()
async def main_handler(message: types.Message):
    if message.from_user is None:
        return None

    if await skip_message(message):
        return

    telemetry.get().incr('messages.main')
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

    is_group = message.chat.type in ['group', 'supergroup']
    send_response = message.reply if is_group else message.answer
    send_photo_response = message.reply_photo if is_group else message.answer_photo
    send_document_response = message.reply_document if is_group else message.answer_document

    user, balance = await asyncio.gather(
        sql_users.get(message.from_user.id),
        sql_wallets.get(message.from_user.id)
    )
    if not user:
        user, balance = await registration(message.from_user)
    if balance <= 0:
        await send_response(NEED_PAY_MSG)
        return

    contents = []
    if message.photo:
        file_params = await tg_bot.get().get_file(message.photo[-1].file_id)
        assert file_params.file_path
        download_url = f"{settings.TELEGRAM_BASE_URL}/file/bot{settings.TG_TOKEN}/{file_params.file_path}"
        contents.append({'type': 'image_url', 'image_url': {'url': download_url}})
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
        contents.append({'type': 'text', 'text': requeset_text})
    if message.caption:
        contents.append({'type': 'text', 'text': message.caption})
    if message.text:
        contents.append({'type': 'text', 'text': message.text})

    if not contents:
        return

    state = await ai.get_chat_state(message)
    answer = await state.send(*contents)
    if isinstance(answer, dict):
        for name, body in answer.items():
            if isinstance(body, str):
                body = body.encode()
            if Path(name).suffix.lower() in ['.jpg', '.png']:
                await send_photo_response(
                    BufferedInputFile(body, name),
                )
            else:
                await send_document_response(
                    BufferedInputFile(body, filename=name),
                )
    elif isinstance(answer, bytes):
        await send_photo_response(
            BufferedInputFile(answer, 'answer.jpg'),
        )
    elif isinstance(answer, str):
        if len(answer) > 4096:
            await send_document_response(
                BufferedInputFile(answer.encode(), filename='answer.txt'),
            )
        else:
            try:
                await send_response(answer)
            except TelegramBadRequest as e:
                if 'can\'t parse entities' in str(e):
                    try:
                        await send_response(answer, parse_mode=ParseMode.HTML)
                    except TelegramBadRequest as e:
                        if 'can\'t parse entities' in str(e):
                            await send_document_response(
                                BufferedInputFile(answer.encode(), filename='answer.txt'),
                            )
                        else:
                            raise
                else:
                    raise


async def run() -> None:
    await tg_bot.get().set_my_commands(
        commands=[
            BotCommand(command='/pay', description='Пополнить баланс'),
            BotCommand(command='/clean', description='Очистить контекст'),
        ],
        scope=types.BotCommandScopeAllPrivateChats(),
    )
    await tg_bot.get().set_my_commands(
        commands=[
            BotCommand(command='/clean', description='Очистить контекст'),
        ],
        scope=types.BotCommandScopeAllGroupChats(),
    )
    await dp.start_polling(tg_bot.get(), handle_signals=False)
