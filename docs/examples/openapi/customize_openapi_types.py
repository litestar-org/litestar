from typing import Literal, Optional

from litestar import Litestar, post
from litestar.params import FromQuery


@post("/")
async def query_type_test(param: FromQuery[Optional[Literal["1"]]]) -> None:
    return None


app = Litestar(route_handlers=[query_type_test])
