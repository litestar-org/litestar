import asyncio
from collections.abc import AsyncGenerator

from litestar import Litestar, websocket_stream

RESOURCE_LOCK = asyncio.Lock()


async def ping_external_resource() -> float:
    return 1.0


@websocket_stream("/")
async def ping() -> AsyncGenerator[float, None]:
    while True:
        async with RESOURCE_LOCK:
            alive = await ping_external_resource()
        yield alive
        await asyncio.sleep(1)


app = Litestar([ping])
