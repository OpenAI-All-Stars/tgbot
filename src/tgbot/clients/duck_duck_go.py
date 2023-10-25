"""
fork of https://github.com/deedy5/duckduckgo_search
"""

import asyncio
from html import unescape
import logging
from datetime import datetime
from random import choice
import re
from typing import AsyncIterator
from urllib.parse import unquote

import httpx


logger = logging.getLogger(__name__)
USERAGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",  # noqa: E501
]
REGEX_500_IN_URL = re.compile(r"(?:\d{3}-\d{2}\.js)")
REGEX_STRIP_TAGS = re.compile("<.*?>")


class AsyncDDGS:
    """DuckDuckgo_search async class to get search results from duckduckgo.com

    Args:
        headers (dict, optional): Dictionary of headers for the HTTP client. Defaults to None.
        proxies (Union[dict, str], optional): Proxies for the HTTP client (can be dict or str). Defaults to None.
        timeout (int, optional): Timeout value for the HTTP client. Defaults to 10.
    """

    def __init__(self, headers=None, proxies=None, timeout=10) -> None:
        if headers is None:
            headers = {
                "User-Agent": choice(USERAGENTS),
                "Referer": "https://duckduckgo.com/",
            }
        self._client = httpx.AsyncClient(headers=headers, proxies=proxies, timeout=timeout, http2=True)

    async def __aenter__(self) -> "AsyncDDGS":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._client.aclose()

    async def _get_url(self, method: str, url: str, **kwargs) -> httpx._models.Response | None:
        for i in range(3):
            try:
                resp = await self._client.request(method, url, follow_redirects=True, **kwargs)
                if _is_500_in_url(str(resp.url)) or resp.status_code == 202:
                    raise httpx._exceptions.HTTPError("")
                resp.raise_for_status()
                if resp.status_code == 200:
                    return resp
            except Exception as ex:
                logger.warning(f"_get_url() {url} {type(ex).__name__} {ex}")
                if i >= 2 or "418" in str(ex):
                    raise ex
            await asyncio.sleep(3)
        return None

    async def _get_vqd(self, keywords: str) -> str | None:
        """Get vqd value for a search query."""
        resp = await self._get_url("POST", "https://duckduckgo.com", data={"q": keywords})
        if resp:
            return _extract_vqd(resp.content)
        return None

    async def text(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        max_results: int | None = None,
    ) -> AsyncIterator[dict[str, str | None]]:
        """DuckDuckGo text search generator. Query params: https://duckduckgo.com/params

        Args:
            keywords: keywords for query.
            region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            safesearch: on, moderate, off. Defaults to "moderate".
            timelimit: d, w, m, y. Defaults to None.
            max_results: max number of results. If None, returns results only from the first response. Defaults to None.
        Yields:
            dict with search results.

        """
        results = self._text_api(keywords, region, safesearch, timelimit, max_results)

        results_counter = 0
        async for result in results:
            yield result
            results_counter += 1
            if max_results and results_counter >= max_results:
                break

    async def _text_api(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        max_results: int | None = None,
    ) -> AsyncIterator[dict[str, str | None]]:
        """DuckDuckGo text search generator. Query params: https://duckduckgo.com/params

        Args:
            keywords: keywords for query.
            region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            safesearch: on, moderate, off. Defaults to "moderate".
            timelimit: d, w, m, y. Defaults to None.
            max_results: max number of results. If None, returns results only from the first response. Defaults to None.

        Yields:
            dict with search results.

        """
        assert keywords, "keywords is mandatory"

        vqd = await self._get_vqd(keywords)
        assert vqd, "error in getting vqd"

        payload = {
            "q": keywords,
            "kl": region,
            "l": region,
            "bing_market": region,
            "s": 0,
            "df": timelimit,
            "vqd": vqd,
            "o": "json",
            "sp": "0",
        }
        safesearch = safesearch.lower()
        if safesearch == "moderate":
            payload["ex"] = "-1"
        elif safesearch == "off":
            payload["ex"] = "-2"
        elif safesearch == "on":  # strict
            payload["p"] = "1"

        cache = set()
        for _ in range(10):
            resp = await self._get_url("GET", "https://links.duckduckgo.com/d.js", params=payload)
            if resp is None:
                return
            try:
                page_data = resp.json().get("results", None)
            except Exception:
                return
            if page_data is None:
                return

            result_exists = False
            for row in page_data:
                href = row.get("u", None)
                if href and href not in cache and href != f"http://www.google.com/search?q={keywords}":
                    cache.add(href)
                    body = _normalize(row["a"])
                    if body:
                        result_exists = True
                        yield {
                            "title": _normalize(row["t"]),
                            "href": _normalize_url(href),
                            "body": body,
                        }
                else:
                    next_page_url = row.get("n", None)
            if max_results is None or result_exists is False or next_page_url is None:
                return
            payload["s"] = next_page_url.split("s=")[1].split("&")[0]

    async def news(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        max_results: int | None = None,
    ) -> AsyncIterator[dict[str, str | None]]:
        """DuckDuckGo news search. Query params: https://duckduckgo.com/params

        Args:
            keywords: keywords for query.
            region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            safesearch: on, moderate, off. Defaults to "moderate".
            timelimit: d, w, m. Defaults to None.
            max_results: max number of results. If None, returns results only from the first response. Defaults to None.

        Yields:
            dict with news search results.

        """
        assert keywords, "keywords is mandatory"

        vqd = await self._get_vqd(keywords)
        assert vqd, "error in getting vqd"

        safesearch_base = {"on": 1, "moderate": -1, "off": -2}
        payload = {
            "l": region,
            "o": "json",
            "noamp": "1",
            "q": keywords,
            "vqd": vqd,
            "p": safesearch_base[safesearch.lower()],
            "df": timelimit,
            "s": 0,
        }

        cache = set()
        for _ in range(10):
            resp = await self._get_url("GET", "https://duckduckgo.com/news.js", params=payload)
            if resp is None:
                return
            try:
                resp_json = resp.json()
            except Exception:
                return
            page_data = resp_json.get("results", None)
            if page_data is None:
                return

            result_exists = False
            for row in page_data:
                if row["url"] not in cache:
                    cache.add(row["url"])
                    image_url = row.get("image", None)
                    result_exists = True
                    yield {
                        "date": datetime.utcfromtimestamp(row["date"]).isoformat(),
                        "title": row["title"],
                        "body": _normalize(row["excerpt"]),
                        "url": _normalize_url(row["url"]),
                        "image": _normalize_url(image_url) if image_url else None,
                        "source": row["source"],
                    }
                    if max_results and len(cache) >= max_results:
                        return
            if max_results is None or result_exists is False:
                return
            next = resp_json.get("next", None)
            if next is None:
                return
            payload["s"] = next.split("s=")[-1].split("&")[0]


def _extract_vqd(html_bytes: bytes) -> str | None:
    for c1, c2 in (
        (b'vqd="', b'"'),
        (b"vqd=", b"&"),
        (b"vqd='", b"'"),
    ):
        try:
            start = html_bytes.index(c1) + len(c1)
            end = html_bytes.index(c2, start)
            return html_bytes[start:end].decode()
        except ValueError:
            pass
    return None


def _is_500_in_url(url: str) -> bool:
    """something like '506-00.js' inside the url"""
    return bool(REGEX_500_IN_URL.search(url))


def _normalize(raw_html: str) -> str:
    """Strip HTML tags from the raw_html string."""
    return unescape(re.sub(REGEX_STRIP_TAGS, "", raw_html)) if raw_html else ""


def _normalize_url(url: str) -> str:
    """Unquote URL and replace spaces with '+'"""
    return unquote(url.replace(" ", "+")) if url else ""
