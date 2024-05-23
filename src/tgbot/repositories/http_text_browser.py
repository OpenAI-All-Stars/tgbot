from markdownify import markdownify

from tgbot.deps import http_client


async def read(url: str) -> str:
    client = http_client.get()
    resp = await client.get(url, allow_redirects=True)
    resp.raise_for_status()
    data = await resp.text()
    return markdownify(data)
