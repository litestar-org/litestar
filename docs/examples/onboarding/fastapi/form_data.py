from typing import Annotated

from litestar import Litestar, post
from litestar.enums import RequestEncodingType
from litestar.params import Body


@post("/login")
async def login(
    data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> dict[str, str]:
    return {"user": data["username"]}


app = Litestar(route_handlers=[login])
