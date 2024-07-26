from markdownify import markdownify

from tgbot.deps import http_client
from tgbot.utils import convert_pdf_to_text


async def read(url: str) -> str:
    client = http_client.get()
    resp = await client.get(url, allow_redirects=True)
    resp.raise_for_status()
    content_type = resp.headers.get('Content-Type', '').lower()
    if 'application/pdf' in content_type:
        data = await resp.read()
        return await convert_pdf_to_text(data)
    data = await resp.text()
    return markdownify(data)
