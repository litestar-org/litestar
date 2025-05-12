from asyncio import sleep
from typing import AsyncGenerator

from litestar import Litestar, get
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.types import SSEData

async def my_slow_generator() -> AsyncGenerator[SSEData, None]:
    count = 0
    while count < 1:
        await sleep(1)
        count += 1
        yield ServerSentEventMessage(data="content", event="message")

@get(path="/with_ping", sync_to_thread=False)
def sse_handler_with_ping_events() -> ServerSentEvent:
    return ServerSentEvent(my_slow_generator(), ping_interval=0.1)


app = Litestar(route_handlers=[sse_handler_with_ping_events])