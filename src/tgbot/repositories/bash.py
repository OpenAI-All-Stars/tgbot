from asyncio import create_subprocess_shell, subprocess


async def execute(command: str) -> str:
    proc = await create_subprocess_shell(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = await proc.communicate()
    return stdout.decode() + stderr.decode()
