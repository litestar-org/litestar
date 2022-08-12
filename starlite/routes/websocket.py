from typing import TYPE_CHECKING, Any, Optional, cast

from starlette.routing import get_name

from starlite.connection import WebSocket
from starlite.controller import Controller
from starlite.enums import ScopeType
from starlite.routes.base import BaseRoute
from starlite.signature import get_signature_model

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable
    from starlette.types import Receive, Scope, Send

    from starlite.handlers.websocket import WebsocketRouteHandler
    from starlite.kwargs import KwargsModel
    from starlite.types import AsyncAnyCallable


class WebSocketRoute(BaseRoute):
    __slots__ = (
        "route_handler",
        "handler_parameter_model"
        # the rest of __slots__ are defined in BaseRoute and should not be duplicated
        # see: https://stackoverflow.com/questions/472000/usage-of-slots
    )

    def __init__(
        self,
        *,
        path: str,
        route_handler: "WebsocketRouteHandler",
    ):
        self.route_handler = route_handler
        self.handler_parameter_model: Optional["KwargsModel"] = None
        super().__init__(
            path=path,
            scope_type=ScopeType.WEBSOCKET,
            handler_names=[get_name(cast("AnyCallable", route_handler.fn))],
        )

    async def handle(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        ASGI app that creates a WebSocket from the passed in args, and then awaits the handler function
        """
        assert self.handler_parameter_model, "handler parameter model not defined"
        route_handler = self.route_handler
        web_socket: WebSocket[Any, Any] = WebSocket(scope=scope, receive=receive, send=send)
        if route_handler.resolve_guards():
            await route_handler.authorize_connection(connection=web_socket)
        signature_model = get_signature_model(route_handler)
        handler_parameter_model = self.handler_parameter_model
        kwargs = handler_parameter_model.to_kwargs(connection=web_socket)
        for dependency in handler_parameter_model.expected_dependencies:
            kwargs[dependency.key] = await self.handler_parameter_model.resolve_dependency(
                dependency=dependency, connection=web_socket, **kwargs
            )
        parsed_kwargs = signature_model.parse_values_from_connection_kwargs(connection=web_socket, **kwargs)
        fn = cast("AsyncAnyCallable", self.route_handler.fn)
        if isinstance(route_handler.owner, Controller):
            await fn(route_handler.owner, **parsed_kwargs)
        else:
            await fn(**parsed_kwargs)
