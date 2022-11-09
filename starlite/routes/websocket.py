from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from starlite.controller import Controller
from starlite.enums import ScopeType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.routes.base import BaseRoute
from starlite.signature import get_signature_model
from starlite.utils import get_name
from starlite.utils.dependency import resolve_dependencies_concurrently

if TYPE_CHECKING:
    from starlite.connection import WebSocket
    from starlite.handlers.websocket import WebsocketRouteHandler
    from starlite.kwargs import KwargsModel
    from starlite.types import (
        AnyCallable,
        AsyncAnyCallable,
        Receive,
        Send,
        WebSocketScope,
    )


class WebSocketRoute(BaseRoute):
    """A websocket route, handling a single `WebsocketRouteHandler`"""

    __slots__ = (
        "route_handler",
        "handler_parameter_model",
    )

    def __init__(
        self,
        *,
        path: str,
        route_handler: "WebsocketRouteHandler",
    ) -> None:
        """Initialize the route.

        Args:
            path: The path for the route.
            route_handler: An instance of [WebsocketRouteHandler][starlite.handlers.websocket.WebsocketRouteHandler].
        """
        self.route_handler = route_handler
        self.handler_parameter_model: Optional["KwargsModel"] = None
        super().__init__(
            path=path,
            scope_type=ScopeType.WEBSOCKET,
            handler_names=[get_name(cast("AnyCallable", route_handler.fn))],
        )

    async def handle(self, scope: "WebSocketScope", receive: "Receive", send: "Send") -> None:  # type: ignore[override]
        """ASGI app that creates a WebSocket from the passed in args, and then
        awaits the handler function.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        websocket: "WebSocket[Any, Any]" = scope["app"].websocket_class(scope=scope, receive=receive, send=send)
        if self.route_handler.resolve_guards():
            await self.route_handler.authorize_connection(connection=websocket)

        kwargs = await self._resolve_kwargs(websocket=websocket)

        fn = cast("AsyncAnyCallable", self.route_handler.fn)
        if isinstance(self.route_handler.owner, Controller):
            await fn(self.route_handler.owner, **kwargs)
        else:
            await fn(**kwargs)

    async def _resolve_kwargs(self, websocket: "WebSocket[Any, Any]") -> Dict[str, Any]:
        """Resolves the required kwargs from the request data.

        Args:
            websocket: WebSocket instance

        Returns:
            Dictionary of parsed kwargs
        """
        if not self.handler_parameter_model:  # pragma: no cover
            raise ImproperlyConfiguredException("handler parameter model not defined")

        signature_model = get_signature_model(self.route_handler)
        kwargs = self.handler_parameter_model.to_kwargs(connection=websocket)
        await resolve_dependencies_concurrently(
            self.handler_parameter_model,
            self.handler_parameter_model.expected_dependencies,
            websocket,
            kwargs,
        )
        return signature_model.parse_values_from_connection_kwargs(connection=websocket, **kwargs)
