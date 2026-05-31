from typing import Annotated

from litestar import Litestar, get
from litestar.params import CookieParameter, HeaderParameter


@get("/")
async def handler(
    session_id: Annotated[str, CookieParameter(name="sessionid")],
    api_key: Annotated[str, HeaderParameter(name="X-API-Key")],
) -> dict[str, str]:
    return {"session": session_id, "api_key": api_key}


app = Litestar(route_handlers=[handler])
