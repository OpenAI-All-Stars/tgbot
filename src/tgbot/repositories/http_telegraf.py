import asyncio
from typing import Any

from simple_settings import settings

from tgbot.deps import http_client


def send(name: str, value: Any):
    if not settings.TELEGRAF_URL:
        return
    asyncio.create_task(http_client.get().post(
        settings.TELEGRAF_URL + '/write',
        data='{}{},value={}'.format(settings.TELEGRAF_PREFIX, name, value),
        raise_for_status=True,
    ))
