from enum import Enum
from os import environ

from pydantic import UUID4, BaseModel

from litestar import Controller, Litestar, Router, get, post
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler


class UserRole(str, Enum):
    CONSUMER = "consumer"
    ADMIN = "admin"


class User(BaseModel):
    id: UUID4
    role: UserRole

    @property
    def is_admin(self) -> bool:
        """Determines whether the user is an admin user"""
        return self.role == UserRole.ADMIN


def admin_user_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    if not connection.user.is_admin:
        raise NotAuthorizedException()


@post(path="/user", guards=[admin_user_guard])
def create_user(data: User) -> User: ...


def my_guard(connection: ASGIConnection, handler: BaseRouteHandler) -> None: ...


# controller
class UserController(Controller):
    path = "/user"
    guards = [my_guard]


# router
admin_router = Router(path="admin", route_handlers=[UserController], guards=[my_guard])

# app
app = Litestar(route_handlers=[admin_router], guards=[my_guard])


def secret_token_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    if (
        route_handler.opt.get("secret")
        and not connection.headers.get("Secret-Header", "") == route_handler.opt["secret"]
    ):
        raise NotAuthorizedException()


@get(path="/secret", guards=[secret_token_guard], opt={"secret": environ.get("SECRET")})
def secret_endpoint() -> None: ...
