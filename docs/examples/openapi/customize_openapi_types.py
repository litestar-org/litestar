from typing import Literal, Optional

from litestar import Litestar, post


@post("/")
async def query_type_test(param: Optional[Literal["1"]]) -> None:
    return None


app = Litestar(route_handlers=[query_type_test])
