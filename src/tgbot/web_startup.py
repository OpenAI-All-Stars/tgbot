import asyncio
from contextlib import asynccontextmanager

from tgbot import deps, tg_server, workers


@asynccontextmanager
async def lifespan(_):
    async with deps.use_all():
        asyncio.create_task(tg_server.run())
        asyncio.create_task(workers.clean_chat_messages_worker.start())
        yield
