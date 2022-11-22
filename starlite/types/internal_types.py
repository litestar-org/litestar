from typing import TYPE_CHECKING, Any, Callable, Dict, Literal, NamedTuple, Type, Union

from starlite.types import Method

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.controller import Controller
    from starlite.handlers.asgi import ASGIRouteHandler
    from starlite.handlers.http import HTTPRouteHandler
    from starlite.handlers.websocket import WebsocketRouteHandler
    from starlite.response import Response
    from starlite.router import Router
    from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
else:
    ASGIRoute = Any
    ASGIRouteHandler = Any
    Controller = Any
    HTTPRoute = Any
    HTTPRouteHandler = Any
    Response = Any
    Router = Any
    Starlite = Any
    WebSocketRoute = Any
    WebsocketRouteHandler = Any

ReservedKwargs = Literal["request", "socket", "headers", "query", "cookies", "state", "data"]
StarliteType = Starlite
RouteHandlerType = Union[HTTPRouteHandler, WebsocketRouteHandler, ASGIRouteHandler]
RouteType = Union[HTTPRoute, WebSocketRoute, ASGIRoute]
ResponseType = Type[Response]
ControllerRouterHandler = Union[Type[Controller], RouteHandlerType, Router, Callable[..., Any]]
RouteHandlerMapItem = Union[WebsocketRouteHandler, ASGIRouteHandler, Dict[Method, HTTPRouteHandler]]


class PathParameterDefinition(NamedTuple):
    """Path parameter tuple."""

    name: str
    full: str
    type: Type
    parser: Callable[[str], Any]
