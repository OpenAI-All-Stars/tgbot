from contextlib import asynccontextmanager
import sqlite3
from typing import AsyncIterator
from aiosqlite import Connection
import aiosqlite
from simple_settings import settings

from tgbot.registry import RegistryValue
from tgbot.clients.duck_duck_go import AsyncDDGS


db = RegistryValue[Connection]()
duck_client = RegistryValue[AsyncDDGS]()


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
async def use_duck() -> AsyncIterator[AsyncDDGS]:
    async with AsyncDDGS() as client:
        duck_client.set(client)
        yield client


@asynccontextmanager
async def use_all() -> AsyncIterator[None]:
    async with (use_db(), use_duck()):
        yield
