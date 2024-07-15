import asyncio
from contextlib import asynccontextmanager

import sentry_sdk
from simple_settings import settings

from tgbot import deps, tg_server


@asynccontextmanager
async def lifespan(_):
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
    async with deps.use_all():
        asyncio.create_task(tg_server.run())
        yield
