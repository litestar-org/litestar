import asyncio
from collections.abc import AsyncGenerator

from litestar import Litestar, websocket_stream

RESOURCE_LOCK = asyncio.Lock()


async def ping_external_resource() -> float:
    return 1.0


async def acquire_lock() -> AsyncGenerator[None, None]:
    async with RESOURCE_LOCK:
        yield


@websocket_stream("/")
async def ping(lock: asyncio.Lock) -> AsyncGenerator[float, None]:
    while True:
        alive = await ping_external_resource()
        yield alive
        await asyncio.sleep(1)


app = Litestar([ping], dependencies={"lock": acquire_lock})
