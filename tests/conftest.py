import asyncio
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Any, AsyncGenerator
from urllib.parse import parse_qs

from aiohttp import web
import aiohttp
import pytest
import docker
import asyncpg
from asyncpg import CannotConnectNowError


logger = logging.getLogger(__name__)


@pytest.fixture(scope='session')
def app_env(mock_server_url, postgres_dsn):
    return {
        'SIMPLE_SETTINGS': 'tgbot.settings.test',
        'TELEGRAM_BASE_URL': mock_server_url,
        'POSTGRES_DSN': postgres_dsn,
        'OPENAI_BASE_URL': mock_server_url,
    }


@pytest.fixture(scope='function')
async def tg_server(settings, mock_server, db_clean, db_create):
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
    set_commands_mock = mock_server.add_request_mock(
        'POST', f'/bot{settings.TG_TOKEN}/setMyCommands',
        response_json={
            'ok': True,
        }
    )

    p = subprocess.Popen(['tgbot', 'server'])
    try:
        if await get_me_mock.wait() and await set_commands_mock.wait():
            yield
    finally:
        p.kill()


@pytest.fixture(scope='session')
async def db(settings) -> AsyncGenerator[asyncpg.Connection, None]:
    conn = await asyncpg.connect(settings.POSTGRES_DSN)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture(scope='function')
async def db_create(db):
    f_name = Path(__file__).parent.parent / 'contrib' / 'postgres.sql'
    with open(f_name) as f:
        queries = f.read().split(';')
    for q in queries:
        if q.strip():
            await db.execute(q)


@pytest.fixture(scope='function')
async def db_clean(db):
    tables = await db.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    for table in tables:
        await db.execute(f'DROP TABLE {table["table_name"]} CASCADE')


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
async def mock_server(mock_server_connect, mock_server_url, healthcheck) -> AsyncGenerator['MockServer', None]:
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
    def __init__(self) -> None:
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
        self._routes: list[dict] = []
        logger = logging.getLogger('aiohttp.access')
        logger.setLevel(logging.WARNING)
    
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
    def _dict_contains(superset: dict, subset: dict) -> bool:
        return all(item in superset.items() for item in subset.items())

    def add_request_mock(
            self,
            method: str,
            path: str,
            response_json: Any,
            request_text: str | None = None,
            request_json: Any = None,
        ) -> MockRequest:
        mock = MockRequest()
        self._routes.append({
            'method': method,
            'path': path,
            'request_text': request_text,
            'request_json': request_json,
            'response_json': response_json,
            'mock': mock,
        })
        return mock

    @web.middleware
    async def _route_middleware(self, request: web.Request, handler):
        logger.info('{} {} {}'.format(request.method, request.path, await request.text()))
        for route in self._routes:
            if route['method'] != request.method:
                continue
            if route['path'] != request.path:
                continue
            if route['request_text'] is not None and request.body_exists:
                request_body = await request.text()
                if route['request_text'] == request_body:
                    route['mock'].requests.append(RequestInfo(
                        text=request_body,
                    ))
                    return web.json_response(route['response_json'])
            elif route['request_json'] is None:
                route['mock'].requests.append(RequestInfo(
                    text=await request.text() if request.body_exists else None,
                ))
                return web.json_response(route['response_json'])
            elif request.body_exists:
                request_body = await request.json()
                if self._dict_contains(request_body, route['request_json']):
                    route['mock'].requests.append(RequestInfo(
                        text=await request.text(),
                    ))
                    return web.json_response(route['response_json'])
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


@pytest.fixture(scope='session')
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


@pytest.fixture(scope='session')
def postgres_dsn(get_free_port):
    client = docker.from_env()

    # Pull the PostgreSQL image
    client.images.pull('postgres:latest')

    try:
        existing_container = client.containers.get('test_postgres')
        existing_container.remove(force=True)
    except docker.errors.NotFound:
        pass

    port = get_free_port()
    container = client.containers.run(
        'postgres:latest',
        name='test_postgres',
        environment={
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpassword',
            'POSTGRES_DB': 'testdb'
        },
        ports={'5432': port},
        detach=True
    )

    # Check if PostgreSQL is ready
    dsn = f'postgresql://testuser:testpassword@localhost:{port}/testdb'
    async def check_postgres():
        for _ in range(30):  # Try for up to 30 seconds
            try:
                conn = await asyncpg.connect(dsn)
                await conn.close()
                break
            except (ConnectionError, CannotConnectNowError):
                await asyncio.sleep(1)
        else:
            raise TimeoutError('Failed to connect to PostgreSQL')

    asyncio.run(check_postgres())

    try:
        yield dsn
    finally:
        container.stop()
        container.remove()
        client.close()
