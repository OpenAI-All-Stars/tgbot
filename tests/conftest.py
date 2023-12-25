import asyncio
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Any
from urllib.parse import parse_qs

from aiohttp import web
import aiohttp
import pytest


@pytest.fixture(scope='session')
def app_env(mock_server_url):
    return {
        'SIMPLE_SETTINGS': 'tgbot.settings.test',
        'TELEGRAM_BASE_URL': mock_server_url,
    }


@pytest.fixture(autouse=True)
async def _server(settings, mock_server) -> str:
    get_me_mock = mock_server.add_request_mock(
        'POST', f'/bot{settings.TG_TOKEN}/getMe',
        response_json={
            'ok': True,
            'result': {
                'id': 1,
                'is_bot': True,
                'first_name': 'durov',
            },
        },
    )

    p = subprocess.Popen(['tgbot', 'server'])
    try:
        if await get_me_mock.wait():
            yield
    finally:
        p.kill()


@pytest.fixture(scope='session')
def repo_root_path() -> str:
    return str(Path(__file__).parent.parent.absolute())


@pytest.fixture(scope='session')
def get_free_port():
    def _get() -> int:
        sock = socket.socket()
        sock.bind(('', 0))
        return sock.getsockname()[1]
    return _get


@pytest.fixture(scope='session')
def mock_server_connect(get_free_port) -> tuple[str, int]:
    return '127.0.0.1', get_free_port()


@pytest.fixture(scope='session')
def mock_server_url(mock_server_connect) -> str:
    return f'http://{mock_server_connect[0]}:{mock_server_connect[1]}'


@pytest.fixture(scope='session')
async def mock_server(mock_server_connect, mock_server_url, healthcheck):
    server = MockServer()
    task = asyncio.create_task(server.start(*mock_server_connect))
    server.add_request_mock(
        'GET', '/ping',
        response_json='OK',
    )
    if not await healthcheck(f'{mock_server_url}/ping', 10):
        raise Exception('mock server start failed')
    try:
        yield server
    finally:
        task.cancel()
        await asyncio.wait([task])


@pytest.fixture(autouse=True)
def _mock_server_clean(mock_server):
    try:
        yield
    finally:
        mock_server.clean()


@dataclass
class RequestInfo:
    text: str | None

    def json(self) -> dict | None:
        if self.text:
            return json.loads(self.text)

    def encode_text(self) -> dict:
        return {
            k: v[0] if len(v) == 1 else v
            for k, v in parse_qs(self.text).items()
        }


class MockRequest:
    def __init__(self, response_json: Any) -> None:
        self.response_json = response_json
        self.requests: list[RequestInfo] = []
    
    @property
    def requests_count(self) -> int:
        return len(self.requests)

    async def wait(self, timeout_s: float = 10) -> bool:
        start = time.monotonic()
        while (time.monotonic() - start) < timeout_s:
            if self.requests:
                return True
            await asyncio.sleep(0.01)
        return False


class MockServer:
    def __init__(self) -> None:
        self._app = web.Application(
            middlewares=[self._route_middleware],
        )
        self._routes: dict[str, MockRequest] = {}
        logger = logging.getLogger('aiohttp.access')
        logger.setLevel(logging.INFO)
    
    async def start(self, host: str, port: int):
        await web._run_app(
            self._app,
            host=host,
            port=port,
            shutdown_timeout=0,
            access_log_format='"%r" %s',
        )
    
    def clean(self):
        self._routes.clear()

    @staticmethod
    def _get_route_key(method: str, path: str) -> str:
        return method + path
    
    def add_request_mock(self, method: str, path: str, response_json: Any) -> MockRequest:
        mock = MockRequest(response_json)
        self._routes[self._get_route_key(method, path)] = mock
        return mock

    @web.middleware
    async def _route_middleware(self, request: web.Request, handler):
        key = self._get_route_key(request.method, request.path)
        mock = self._routes.get(key)
        if mock:
            mock.requests.append(
                RequestInfo(
                    text=await request.text(),
                )
            )
            return web.json_response(mock.response_json)
        raise web.HTTPNotFound()


@pytest.fixture(scope='session')
def healthcheck() -> bool:
    async def _check(ping_url: str, retries: int):
        async with aiohttp.ClientSession() as client:
            for _ in range(retries):
                time.sleep(1)
                try:
                    resp = await client.get(ping_url, timeout=1)
                    if resp.status == 200:
                        return True
                except aiohttp.ClientError:
                    pass
        return False
    return _check


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope='session')
def settings(app_env) -> dict:
    os.environ.update(app_env)

    from simple_settings import settings

    return settings
