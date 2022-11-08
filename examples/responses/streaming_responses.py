from asyncio import sleep
from datetime import datetime
from typing import AsyncGenerator

from orjson import dumps

from starlite import Starlite, Stream, get


async def my_generator() -> AsyncGenerator[bytes, None]:
    while True:
        await sleep(0.01)
        yield dumps({"current_time": datetime.now()})


@get(path="/time")
def stream_time() -> Stream:
    return Stream(iterator=my_generator())


app = Starlite(route_handlers=[stream_time])
