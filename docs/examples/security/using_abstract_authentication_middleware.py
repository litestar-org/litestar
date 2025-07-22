from dataclasses import dataclass
from typing import Any

import anyio

from litestar import Litestar, MediaType, Request, Response, WebSocket, get, websocket
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException, NotFoundException
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from litestar.middleware.base import DefineMiddleware

API_KEY_HEADER = "X-API-KEY"

TOKEN_USER_DATABASE = {"1": "user_authorized"}


@dataclass
class MyUser:
    name: str


@dataclass
class MyToken:
    api_key: str


class CustomAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        """Given a request, parse the request api key stored in the header and retrieve the user correlating to the token from the DB"""

        # retrieve the auth header
        auth_header = connection.headers.get(API_KEY_HEADER)
        if not auth_header:
            raise NotAuthorizedException()

        # this would be a database call
        token = MyToken(api_key=auth_header)
        user = MyUser(name=TOKEN_USER_DATABASE.get(token.api_key))
        if not user.name:
            raise NotAuthorizedException()
        return AuthenticationResult(user=user, auth=token)


@get("/")
def my_http_handler(request: Request[MyUser, MyToken, State]) -> None:
    user = request.user  # correctly typed as MyUser
    auth = request.auth  # correctly typed as MyToken
    assert isinstance(user, MyUser)
    assert isinstance(auth, MyToken)


@websocket("/")
async def my_ws_handler(socket: WebSocket[MyUser, MyToken, State]) -> None:
    user = socket.user  # correctly typed as MyUser
    auth = socket.auth  # correctly typed as MyToken
    assert isinstance(user, MyUser)
    assert isinstance(auth, MyToken)


@get(path="/", exclude_from_auth=True)
async def site_index() -> Response:
    """Site index"""
    exists = await anyio.Path("index.html").exists()
    if exists:
        async with await anyio.open_file(anyio.Path("index.html")) as file:
            content = await file.read()
            return Response(content=content, status_code=200, media_type=MediaType.HTML)
    raise NotFoundException("Site index was not found")


async def my_dependency(request: Request[MyUser, MyToken, State]) -> Any:
    user = request.user  # correctly typed as MyUser
    auth = request.auth  # correctly typed as MyToken
    assert isinstance(user, MyUser)
    assert isinstance(auth, MyToken)


# you can optionally exclude certain paths from authentication.
# the following excludes all routes mounted at or under `/schema*`
auth_mw = DefineMiddleware(CustomAuthenticationMiddleware, exclude="schema")

app = Litestar(
    route_handlers=[site_index, my_http_handler, my_ws_handler],
    middleware=[auth_mw],
    dependencies={"some_dependency": Provide(my_dependency)},
)
