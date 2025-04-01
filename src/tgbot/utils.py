import asyncio
import functools
import io
import logging
import re
import time
from typing import AsyncIterator, Awaitable, Callable, Iterable


from aiogram import types
import pymupdf


logger = logging.getLogger(__name__)
HEADER_REGEX = re.compile(r'^###\s*(.*)$', re.MULTILINE)


def async_command(f: Callable) -> Callable:
    @functools.wraps(f)
    def decorator(*args, **kwargs) -> None:
        asyncio.get_event_loop().run_until_complete(f(*args, **kwargs))
    return decorator


async def tick_iterator(interval_s: float) -> AsyncIterator:
    while True:
        start_at = time.time()
        yield
        gone = time.time() - start_at
        left = interval_s - gone
        if left > 0:
            await asyncio.sleep(left)


def get_sign(num: int | float) -> str:
    return '-' if num < 0 else ''


class worker:
    def __init__(self, timeout_s: float):
        self.timeout_s = timeout_s

    def __call__(self, f: Callable[[], Awaitable[None]]) -> 'worker':
        self.f = f
        return self

    async def start(self):
        while True:
            try:
                await self.f()
            except Exception as e:
                logger.exception(e)
            await asyncio.sleep(self.timeout_s)


async def convert_pdf_to_text(data: bytes | io.BytesIO) -> str:
    return await asyncio.get_running_loop().run_in_executor(
        None,
        sync_convert_pdf_to_text,
        data,
    )


def sync_convert_pdf_to_text(data: bytes | io.BytesIO) -> str:
    doc = pymupdf.open(stream=data, filetype='pdf')
    pages: Iterable[pymupdf.Page] = doc.pages()
    return ''.join(
        page.get_textpage().extractText()
        for page in pages
    )


def fix_invalid_markdown(text: str) -> str:
    return HEADER_REGEX.sub(lambda m: f'**{m.group(1)}**', text)


async def skip_message(message: types.Message) -> bool:
    assert message.bot
    me = await message.bot.me()

    if message.chat.type == 'private':
        return False
    if message.chat.type not in ['group', 'supergroup']:
        return True
    if message.text and f"@{me.username}" in message.text:
        return False
    elif (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == me.id
    ):
        return False
    return True
