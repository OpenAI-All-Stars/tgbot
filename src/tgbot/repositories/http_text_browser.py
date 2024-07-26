import asyncio
from typing import Iterable
import pymupdf
from markdownify import markdownify

from tgbot.deps import http_client


async def read(url: str) -> str:
    client = http_client.get()
    resp = await client.get(url, allow_redirects=True)
    resp.raise_for_status()
    content_type = resp.headers.get('Content-Type', '').lower()
    if 'application/pdf' in content_type:
        data = await resp.read()
        data = await asyncio.get_running_loop().run_in_executor(
            None,
            convert_pdf_to_text,
            data,
        )
        return data
    data = await resp.text()
    return markdownify(data)


def convert_pdf_to_text(data):
    doc = pymupdf.open(stream=data, filetype='pdf')
    pages: Iterable[pymupdf.Page] = doc.pages()
    return ''.join(
        page.get_textpage().extractText()
        for page in pages
    )
