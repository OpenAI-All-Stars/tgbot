import asyncio
import functools
import time
from typing import AsyncIterator, Callable


def async_command(f: Callable) -> Callable:
    @functools.wraps(f)
    def decorator(*args, **kwargs) -> None:
        asyncio.get_event_loop().run_until_complete(f(*args, **kwargs))
    return decorator


async def tick_iterator(interval_s: float) -> AsyncIterator:
    while True:
        start_at = time.time()
        yield
        gone = time.time() - start_at
        left = interval_s - gone
        if left > 0:
            await asyncio.sleep(left)
