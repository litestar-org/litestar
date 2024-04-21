from typing import Annotated

import msgspec
from litestar import post, Litestar
from litestar.dto import MsgspecDTO


class Request(msgspec.Struct):
    foo: Annotated[str, msgspec.Meta(min_length=3)]


@post("/example/", dto=MsgspecDTO[Request])
async def example(data: Request) -> Request:
    return data