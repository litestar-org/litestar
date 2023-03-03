from asyncio import sleep
from datetime import datetime
from typing import AsyncGenerator

from starlite import Starlite, get
from starlite.response_containers import Stream
from starlite.serialization import encode_json


async def my_generator() -> AsyncGenerator[bytes, None]:
    while True:
        await sleep(0.01)
        yield encode_json({"current_time": datetime.now()})


@get(path="/time")
def stream_time() -> Stream:
    return Stream(iterator=my_generator())


app = Starlite(route_handlers=[stream_time])
