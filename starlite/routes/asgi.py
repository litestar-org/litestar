from typing import TYPE_CHECKING, Any

from starlite.connection import ASGIConnection
from starlite.enums import ScopeType
from starlite.routes.base import BaseRoute
from starlite.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from starlite.handlers.asgi import ASGIRouteHandler
    from starlite.types import Receive, Scope, Send


class ASGIRoute(BaseRoute):
    """An ASGI route, handling a single `ASGIRouteHandler`"""

    __slots__ = ("route_handler",)

    def __init__(
        self,
        *,
        path: str,
        route_handler: "ASGIRouteHandler",
    ) -> None:
        """Initialize the route.

        Args:
            path: The path for the route.
            route_handler: An instance of [ASGIRouteHandler][starlite.handlers.asgi.ASGIRouteHandler].
        """
        self.route_handler = route_handler
        super().__init__(
            path=path,
            scope_type=ScopeType.ASGI,
            handler_names=[unwrap_partial(route_handler.handler_name)],
        )

    async def handle(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI app that authorizes the connection and then awaits the handler function.

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

        await self.route_handler.fn.value(scope=scope, receive=receive, send=send)
