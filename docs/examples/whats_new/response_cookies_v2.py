from litestar import get


@get("/", response_cookies={"foo": "bar"})
async def handler() -> None: ...
