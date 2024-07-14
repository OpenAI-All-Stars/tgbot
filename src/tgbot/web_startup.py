import asyncio
from contextlib import asynccontextmanager

from tgbot import deps, tg_server


@asynccontextmanager
async def lifespan(_):
    async with deps.use_all():
        asyncio.create_task(tg_server.run())
        yield
