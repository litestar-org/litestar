from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

from typing_extensions import TypeAliasType

from litestar.template.config import EngineType

__all__ = (
    "ControllerRouterHandler",
    "PathParameterDefinition",
    "PathParameterDefinition",
    "ReservedKwargs",
    "RouteHandlerMapItem",
    "RouteHandlerType",
)

if TYPE_CHECKING:
    from litestar.controller import Controller
    from litestar.handlers import BaseRouteHandler
    from litestar.handlers.asgi_handlers import ASGIRouteHandler
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.handlers.websocket_handlers import WebsocketRouteHandler
    from litestar.router import Router
    from litestar.template import TemplateConfig
    from litestar.types import Method


ReservedKwargs = TypeAliasType(
    "ReservedKwargs", Literal["request", "socket", "headers", "query", "cookies", "state", "data"]
)
RouteHandlerType = TypeAliasType("RouteHandlerType", "HTTPRouteHandler | WebsocketRouteHandler | ASGIRouteHandler")
ControllerRouterHandler = TypeAliasType(
    "ControllerRouterHandler", "type[Controller] | RouteHandlerType | Router | Callable[..., Any]"
)
RouteHandlerMapItem = TypeAliasType(
    "RouteHandlerMapItem", 'dict[Method | Literal["websocket", "asgi"], BaseRouteHandler]'
)
TemplateConfigType = TypeAliasType("TemplateConfigType", "TemplateConfig[EngineType]", type_params=(EngineType,))


class PathParameterDefinition(NamedTuple):
    """Path parameter tuple."""

    name: str
    full: str
    type: type
    parser: Callable[[str], Any] | None
