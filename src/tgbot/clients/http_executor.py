from urllib.parse import urljoin

import aiohttp
import asyncio
import backoff
from simple_settings import settings

from tgbot.deps import http_client
from tgbot.entities.executor import ExecuteBashResponse


@backoff.on_exception(backoff.constant, (aiohttp.ClientError, asyncio.TimeoutError), max_tries=3)
async def execute_bash(command: str) -> ExecuteBashResponse:
    client = http_client.get()
    resp = await client.post(
        urljoin(settings.EXECUTOR_BASE_URL, '/execute-bash'),
        json={'command': command},
    )
    resp.raise_for_status()
    return ExecuteBashResponse(**await resp.json())
