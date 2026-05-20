from typing import Literal

from litestar import Litestar, post
from litestar.params import FromQuery


@post("/")
async def query_type_test(param: FromQuery[Literal["1"] | None]) -> None:
    return None


app = Litestar(route_handlers=[query_type_test])
