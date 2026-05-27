from collections.abc import AsyncIterator

from litestar import Litestar, get
from litestar.response import Stream


async def event_source() -> AsyncIterator[bytes]:
    for i in range(3):
        yield f"data: {i}\n\n".encode()


@get("/stream")
async def stream() -> Stream:
    return Stream(event_source(), media_type="text/event-stream")


app = Litestar(route_handlers=[stream])
