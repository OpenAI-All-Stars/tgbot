from contextlib import asynccontextmanager
import contextvars

import asyncpg


_current_connection = contextvars.ContextVar('current_connection')


class Pool(asyncpg.Pool):
    @asynccontextmanager
    async def transaction(self):
        if _current_connection.get(None):
            yield
            return
        async with self.acquire() as con:
            async with con.transaction():
                token = _current_connection.set(con)
                try:
                    yield
                finally:
                    _current_connection.reset(token)

    async def execute(self, query: str, *args, timeout: float | None = None) -> str:
        conn = _current_connection.get(super())
        return await conn.execute(query, *args, timeout=timeout)

    async def executemany(self, command: str, args, *, timeout: float | None = None):
        conn = _current_connection.get(super())
        return await conn.executemany(command, args, timeout=timeout)

    async def fetch(
            self,
            query,
            *args,
            timeout=None,
            record_class=None,
    ) -> list:
        conn = _current_connection.get(super())
        return await conn.fetch(
            query,
            *args,
            timeout=timeout,
            record_class=record_class
        )

    async def fetchval(self, query, *args, column=0, timeout=None):
        conn = _current_connection.get(super())
        return await conn.fetchval(query, *args, column=column, timeout=timeout)

    async def fetchrow(self, query, *args, timeout=None, record_class=None):
        conn = _current_connection.get(super())
        return await conn.fetchrow(
            query,
            *args,
            timeout=timeout,
            record_class=record_class
        )


def create_pool(dsn=None, *,
                min_size=10,
                max_size=10,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,
                setup=None,
                init=None,
                loop=None,
                connection_class=asyncpg.connection.Connection,
                record_class=asyncpg.protocol.Record,
                **connect_kwargs):
    return Pool(
        dsn,
        connection_class=connection_class,
        record_class=record_class,
        min_size=min_size, max_size=max_size,
        max_queries=max_queries, loop=loop, setup=setup, init=init,
        max_inactive_connection_lifetime=max_inactive_connection_lifetime,
        **connect_kwargs)
