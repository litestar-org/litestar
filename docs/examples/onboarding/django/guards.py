from typing import Dict

from litestar import Controller, Litestar, get
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers import BaseRouteHandler


def require_admin(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    if connection.headers.get("x-role") != "admin":
        raise NotAuthorizedException(detail="admin only")


class AdminController(Controller):
    path = "/admin"
    guards = [require_admin]

    @get("/stats")
    async def stats(self) -> Dict[str, int]:
        return {"users": 100}


app = Litestar(route_handlers=[AdminController])
