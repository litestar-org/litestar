from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Literal,
    NamedTuple,
    Union,
)

__all__ = (
    "ControllerRouterHandler",
    "LitestarType",
    "PathParameterDefinition",
    "PathParameterDefinition",
    "ReservedKwargs",
    "ResponseType",
    "RouteHandlerMapItem",
    "RouteHandlerType",
)


if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from litestar.app import Litestar
    from litestar.controller import Controller
    from litestar.handlers.asgi_handlers import ASGIRouteHandler
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.handlers.websocket_handlers import WebsocketRouteHandler
    from litestar.response import Response
    from litestar.router import Router
    from litestar.types import Method

    ReservedKwargs: TypeAlias = Literal["request", "socket", "headers", "query", "cookies", "state", "data"]
    LitestarType: TypeAlias = Litestar
    RouteHandlerType: TypeAlias = Union[HTTPRouteHandler, WebsocketRouteHandler, ASGIRouteHandler]
    ResponseType: TypeAlias = type[Response]
    ControllerRouterHandler: TypeAlias = Union[type[Controller], RouteHandlerType, Router, Callable[..., Any]]
    RouteHandlerMapItem: TypeAlias = Dict[Union[Method, Literal["websocket", "asgi"]], RouteHandlerType]
else:
    ReservedKwargs: TypeAlias = Any
    LitestarType: TypeAlias = Any
    RouteHandlerType: TypeAlias = Any
    ResponseType: TypeAlias = Any
    ControllerRouterHandler: TypeAlias = Any
    RouteHandlerMapItem: TypeAlias = Any


class PathParameterDefinition(NamedTuple):
    """Path parameter tuple."""

    name: str
    full: str
    type: type
    parser: Callable[[str], Any] | None
