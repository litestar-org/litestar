from litestar import get
from litestar.datastructures import Cookie


@get("/", response_cookies=[Cookie(key="foo", value="bar")])
async def handler() -> None: ...
