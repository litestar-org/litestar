from pydantic import BaseModel

from starlite import NotAuthorizedException, Parameter, Starlite, get

USER_DB = {
    1: {
        "id": 1,
        "name": "John Doe",
    },
}

VALID_TOKEN = "super-secret-secret"
VALID_COOKIE_VALUE = "cookie-secret"


class User(BaseModel):
    id: int
    name: str


@get(path="/users/{user_id:int}/")
async def get_user(
    user_id: int,
    token: str = Parameter(header="X-API-KEY"),
    cookie: str = Parameter(cookie="my-cookie-param"),
) -> User:
    if not (token == VALID_TOKEN and cookie == VALID_COOKIE_VALUE):
        raise NotAuthorizedException
    return User.parse_obj(USER_DB[user_id])


app = Starlite(route_handlers=[get_user])
