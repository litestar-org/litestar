from litestar import get


@get(response_cookies={"my-cookie": "cookie-value"})
async def handler() -> str: ...
