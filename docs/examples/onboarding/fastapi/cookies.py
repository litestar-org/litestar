from litestar import Litestar, get
from litestar.datastructures import Cookie


@get("/", response_cookies=[Cookie(key="my-cookie", value="cookie-value")])
async def handler() -> str:
    return "hello"


app = Litestar(route_handlers=[handler])
