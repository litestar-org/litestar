from typing import Annotated

from pydantic import BaseModel
import dataclasses

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.exceptions import NotAuthorizedException
from litestar.params import CookieParameter, FromPath, HeaderParameter

VALID_TOKEN = "super-secret-secret"
VALID_COOKIE_VALUE = "cookie-secret"


@dataclasses.dataclass
class User:
    id: int
    name: str


USER_DB = {
    1: User(id=1, name="John Doe"),
}


@get(path="/users/{user_id:int}/")
async def get_user(
    user_id: FromPath[int],
    token: Annotated[str, HeaderParameter(name="X-API-KEY")],
    cookie: Annotated[str, CookieParameter(name="my-cookie-param")],
) -> User:
    if token != VALID_TOKEN or cookie != VALID_COOKIE_VALUE:
        raise NotAuthorizedException
    return USER_DB[user_id]


app = Litestar(route_handlers=[get_user])
