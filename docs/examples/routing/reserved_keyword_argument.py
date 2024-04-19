from typing import Any, Dict
from litestar import Request, get
from litestar.datastructures import Headers, State


@get(path="/")
async def my_request_handler(
        state: State,
        request: Request,
        headers: Dict[str, str],
        query: Dict[str, Any],
        cookies: Dict[str, Any],
) -> None: ...