from contextlib import asynccontextmanager
import sqlite3
from typing import AsyncIterator
from aiohttp import ClientSession
from aiosqlite import Connection
import aiosqlite
from simple_settings import settings

from tgbot.registry import RegistryValue


db = RegistryValue[Connection]()
http_client = RegistryValue[ClientSession]()


@asynccontextmanager
async def use_db() -> AsyncIterator[Connection]:
    conn = await aiosqlite.connect(settings.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    db.set(conn)
    try:
        yield conn
    finally:
        await conn.close()


@asynccontextmanager
async def use_http_client() -> AsyncIterator[ClientSession]:
    async with ClientSession() as client:
        http_client.set(client)
        yield client


@asynccontextmanager
async def use_all() -> AsyncIterator[None]:
    async with (use_db(), use_http_client()):
        yield
