from asyncio import sleep
from typing import AsyncGenerator

from litestar import Litestar, get
from litestar.response import ServerSentEventStream


async def my_generator() -> AsyncGenerator[bytes, None]:
    count = 0
    while count < 10:
        await sleep(0.01)
        count += 1
        yield str(count)


@get(path="/count", sync_to_thread=False)
def sse_handler() -> ServerSentEventStream:
    return ServerSentEventStream(my_generator())


app = Litestar(route_handlers=[sse_handler])
