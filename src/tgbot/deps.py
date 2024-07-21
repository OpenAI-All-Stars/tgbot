from contextlib import asynccontextmanager
from typing import AsyncIterator

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiohttp import ClientSession
import httpx
from simple_settings import settings
from openai import AsyncOpenAI

from tgbot.pool_wrapper import Pool, create_pool
from tgbot.registry import RegistryValue


db = RegistryValue[Pool]()
http_client = RegistryValue[ClientSession]()
openai_client = RegistryValue[AsyncOpenAI]()
tg_bot = RegistryValue[Bot]()


@asynccontextmanager
async def use_db() -> AsyncIterator[Pool]:
    async with create_pool(settings.POSTGRES_DSN) as pool:
        db.set(pool)
        yield pool


@asynccontextmanager
async def use_http_client() -> AsyncIterator[ClientSession]:
    async with ClientSession() as client:
        http_client.set(client)
        yield client


@asynccontextmanager
async def use_openai_client() -> AsyncIterator[AsyncOpenAI]:
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=httpx.AsyncClient(
            base_url=settings.OPENAI_BASE_URL,
            proxy=settings.PROXY,
            follow_redirects=True,
            timeout=httpx.Timeout(timeout=60.0),
        )
    )
    openai_client.set(client)
    try:
        yield client
    finally:
        await client.close()


@asynccontextmanager
async def use_tg_bot() -> AsyncIterator[Bot]:
    bot = Bot(
        settings.TG_TOKEN,
        parse_mode=ParseMode.MARKDOWN,
        session=AiohttpSession(
            proxy=settings.TG_PROXY,
            api=TelegramAPIServer.from_base(settings.TELEGRAM_BASE_URL),
        ),
    )
    tg_bot.set(bot)
    yield bot


@asynccontextmanager
async def use_all() -> AsyncIterator[None]:
    async with (use_db(), use_http_client(), use_openai_client(), use_tg_bot()):
        yield
