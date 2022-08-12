from typing import TYPE_CHECKING, cast

from starlette.requests import HTTPConnection
from starlette.routing import get_name

from starlite.controller import Controller
from starlite.enums import ScopeType
from starlite.routes.base import BaseRoute

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable
    from starlette.types import Receive, Scope, Send

    from starlite.handlers.asgi import ASGIRouteHandler


class ASGIRoute(BaseRoute):
    __slots__ = (
        "route_handler",
        # the rest of __slots__ are defined in BaseRoute and should not be duplicated
        # see: https://stackoverflow.com/questions/472000/usage-of-slots
    )

    def __init__(
        self,
        *,
        path: str,
        route_handler: "ASGIRouteHandler",
    ):
        self.route_handler = route_handler
        super().__init__(
            path=path,
            scope_type=ScopeType.ASGI,
            handler_names=[get_name(cast("AnyCallable", route_handler.fn))],
        )

    async def handle(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        ASGI app that authorizes the connection and then awaits the handler function
        """

        if self.route_handler.resolve_guards():
            connection = HTTPConnection(scope=scope, receive=receive)
            await self.route_handler.authorize_connection(connection=connection)

        fn = cast("AnyCallable", self.route_handler.fn)
        if isinstance(self.route_handler.owner, Controller):
            await fn(self.route_handler.owner, scope=scope, receive=receive, send=send)
        else:
            await fn(scope=scope, receive=receive, send=send)
