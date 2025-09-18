from typing import Literal, Union

from litestar import Litestar, post


@post("/")
async def query_type_test(param: Union[Literal["1"], None]) -> None:
    return None


app = Litestar(route_handlers=[query_type_test])
