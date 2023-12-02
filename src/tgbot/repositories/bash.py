from tgbot.clients import http_executor


async def execute(command: str) -> str:
    resp = await http_executor.execute_bash(command)
    return resp.stdout + resp.stderr
