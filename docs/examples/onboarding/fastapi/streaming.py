from collections.abc import AsyncIterator

from litestar import Litestar, get
from litestar.response import Stream


async def numbers() -> AsyncIterator[bytes]:
    for i in range(5):
        yield f"{i}\n".encode()


@get("/numbers")
async def stream_numbers() -> Stream:
    return Stream(numbers())


app = Litestar(route_handlers=[stream_numbers])
