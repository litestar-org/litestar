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

from litestar.types import Method

__all__ = (
    "PathParameterDefinition",
    "ControllerRouterHandler",
    "ReservedKwargs",
    "ResponseType",
    "RouteHandlerMapItem",
    "RouteHandlerType",
)


if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.controller import Controller
    from litestar.handlers.asgi_handlers import ASGIRouteHandler
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.handlers.websocket_handlers import WebsocketRouteHandler
    from litestar.response import Response
    from litestar.router import Router
else:
    Litestar = Any
    ASGIRouteHandler = Any
    WebsocketRouteHandler = Any
    HTTPRouteHandler = Any
    Response = Any
    Controller = Any
    Router = Any

ReservedKwargs = Literal["request", "socket", "headers", "query", "cookies", "state", "data"]
LitestarType = Litestar
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
