from litestar import get


@get(response_headers={"my-header": "header-value"})
async def handler() -> str: ...
