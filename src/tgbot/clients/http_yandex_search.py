import asyncio
import json
import logging
from xml.etree import ElementTree

import aiohttp
import backoff
from simple_settings import settings

from tgbot.deps import http_client


logger = logging.getLogger(__name__)


@backoff.on_exception(backoff.constant, (aiohttp.ClientError, asyncio.TimeoutError), max_tries=3)
async def search(query: str) -> str:
    client = http_client.get()
    resp = await client.get(
            settings.YANDEX_SEARCH_URL,
            params={
                'apikey': settings.YANDEX_SEARCH_API_KEY,
                'folderid': settings.YANDEX_FOLDERID,
                'filter': 'none',
                'lr': '225',
                'l10n': 'ru',
                'query': query,
                'page': 1,

            },
        )
    resp.raise_for_status()
    data = await resp.text()

    root = ElementTree.fromstring(data)

    results = []
    for doc in root.iter('doc'):
        description = []
        e = doc.find('charset')
        charset = e.text if e else 'utf-8'
        passages = doc.find('passages')
        if passages:
            for passage in passages:
                description.append(ElementTree.tostring(passage, encoding=charset, method='text').decode())
        else:
            title = doc.find('title')
            if title:
                description.append(ElementTree.tostring(title, encoding=charset, method='text').decode())

        e = doc.find('url')
        if e:
            results.append({
                'url': e.text,
                'description': '\n'.join(description)
            })

    if not results:
        logger.error(f'search fail: {data}')

    return json.dumps(results)
