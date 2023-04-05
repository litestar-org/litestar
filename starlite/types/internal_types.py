from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Literal,
    NamedTuple,
    Optional,
    Type,
    Union,
)

from starlite.types import Method

__all__ = (
    "PathParameterDefinition",
    "ControllerRouterHandler",
    "ReservedKwargs",
    "ResponseType",
    "RouteHandlerMapItem",
    "RouteHandlerType",
)


if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.controller import Controller
    from starlite.handlers.asgi_handlers import ASGIRouteHandler
    from starlite.handlers.http_handlers import HTTPRouteHandler
    from starlite.handlers.websocket_handlers import WebsocketRouteHandler
    from starlite.response import Response
    from starlite.router import Router
else:
    Starlite = Any
    ASGIRouteHandler = Any
    WebsocketRouteHandler = Any
    HTTPRouteHandler = Any
    Response = Any
    Controller = Any
    Router = Any

ReservedKwargs = Literal["request", "socket", "headers", "query", "cookies", "state", "data"]
StarliteType = Starlite
RouteHandlerType = Union[HTTPRouteHandler, WebsocketRouteHandler, ASGIRouteHandler]
ResponseType = Type[Response]
ControllerRouterHandler = Union[Type[Controller], RouteHandlerType, Router, Callable[..., Any]]
RouteHandlerMapItem = Dict[Union[Method, Literal["websocket", "asgi"]], RouteHandlerType]


class PathParameterDefinition(NamedTuple):
    """Path parameter tuple."""

    name: str
    full: str
    type: Type
    parser: Optional[Callable[[str], Any]]
