from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Literal, NamedTuple

__all__ = (
    "ControllerRouterHandler",
    "PathParameterDefinition",
    "PathParameterDefinition",
    "ReservedKwargs",
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
    from litestar.router import Router
    from litestar.template import TemplateConfig
    from litestar.template.config import EngineType
    from litestar.types import Method

ReservedKwargs: TypeAlias = Literal["request", "socket", "headers", "query", "cookies", "state", "data"]
RouteHandlerType: TypeAlias = "HTTPRouteHandler | WebsocketRouteHandler | ASGIRouteHandler"
ControllerRouterHandler: TypeAlias = "type[Controller] | RouteHandlerType | Router | Callable[..., Any]"
RouteHandlerMapItem: TypeAlias = 'dict[Method | Literal["websocket", "asgi"], RouteHandlerType]'
TemplateConfigType: TypeAlias = "TemplateConfig[EngineType]"

# deprecated
_LitestarType: TypeAlias = "Litestar"


class PathParameterDefinition(NamedTuple):
    """Path parameter tuple."""

    name: str
    full: str
    type: type
    parser: Callable[[str], Any] | None
