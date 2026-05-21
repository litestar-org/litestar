from typing import Annotated

from litestar import get
from litestar.params import CookieParameter, HeaderParameter


@get("/")
async def handler(
    some_cookie: Annotated[str, CookieParameter(lt=10)],
    some_header: Annotated[int, HeaderParameter(name="some-header", gt=1)],
) -> None:
    return None
