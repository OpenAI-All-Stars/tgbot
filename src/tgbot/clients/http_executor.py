import httpx
from simple_settings import settings

from tgbot.entities.executor import ExecuteBashResponse


async def execute_bash(command: str) -> ExecuteBashResponse:
    async with httpx.AsyncClient(base_url=settings.EXECUTOR_BASE_URL) as client:
        resp = await client.post('/execute-bash', json={'command': command})
        resp.raise_for_status()
        return ExecuteBashResponse(**resp.json())
