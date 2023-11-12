from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Any
from uuid import UUID

from litestar import Request, Response, get, post
from litestar.connection import ASGIConnection
from litestar.security.jwt import JWTAuth, Token
from litestar.status_codes import HTTP_204_NO_CONTENT
from litestar.testing import create_test_client


@dataclass
class User:
    id: UUID
    name: str
    email: str


MOCK_DB: dict[str, User] = {}


async def retrieve_user_handler(token: Token, connection: ASGIConnection[Any, Any, Any, Any]) -> User | None:
    return MOCK_DB.get(token.sub)


jwt_auth = JWTAuth[User](
    retrieve_user_handler=retrieve_user_handler,
    token_secret=environ.get("JWT_SECRET", "abcd123"),
    exclude=["/login", "/schema"],
)


@post("/login")
async def login_handler(data: User) -> Response[User]:
    MOCK_DB[str(data.id)] = data
    return jwt_auth.login(identifier=str(data.id), response_body=data)


@get("/some-path", sync_to_thread=False)
def some_route_handler(request: Request[User, Token, Any]) -> Any:
    assert isinstance(request.user, User)


def test_options_request_with_jwt() -> None:
    with create_test_client(
        route_handlers=[login_handler, some_route_handler],
        on_app_init=[jwt_auth.on_app_init],
    ) as client:
        response = client.options("/some-path")
        assert response.status_code == HTTP_204_NO_CONTENT
