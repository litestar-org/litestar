from typing import TYPE_CHECKING, Any, cast

from starlette.routing import get_name

from starlite.connection import ASGIConnection
from starlite.controller import Controller
from starlite.enums import ScopeType
from starlite.routes.base import BaseRoute

if TYPE_CHECKING:
    from starlite.handlers.asgi import ASGIRouteHandler
    from starlite.types import AnyCallable, Receive, Scope, Send


class ASGIRoute(BaseRoute):
    __slots__ = ("route_handler",)

    def __init__(
        self,
        *,
        path: str,
        route_handler: "ASGIRouteHandler",
    ) -> None:
        """This class handles a single ASGI Route.

        Args:
            path: The path for the route.
            route_handler: An instance of [ASGIRouteHandler][starlite.handlers.asgi.ASGIRouteHandler].
        """
        self.route_handler = route_handler
        super().__init__(
            path=path,
            scope_type=ScopeType.ASGI,
            handler_names=[get_name(cast("AnyCallable", route_handler.fn))],
        )

    async def handle(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI app that authorizes the connection and then awaits the handler
        function.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """

        if self.route_handler.resolve_guards():
            connection = ASGIConnection["ASGIRouteHandler", Any, Any](scope=scope, receive=receive)
            await self.route_handler.authorize_connection(connection=connection)

        fn = cast("AnyCallable", self.route_handler.fn)
        if isinstance(self.route_handler.owner, Controller):
            await fn(self.route_handler.owner, scope=scope, receive=receive, send=send)
        else:
            await fn(scope=scope, receive=receive, send=send)
