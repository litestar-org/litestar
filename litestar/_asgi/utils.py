from __future__ import annotations

from typing import TYPE_CHECKING, cast

__all__ = ("get_route_handlers", "wrap_in_exception_handler")


if TYPE_CHECKING:
    from litestar.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from litestar.routes.base import BaseRoute
    from litestar.types import ASGIApp, RouteHandlerType


def wrap_in_exception_handler(app: ASGIApp) -> ASGIApp:
    """Wrap the given ASGIApp in an instance of ExceptionHandlerMiddleware.

    Args:
        app: The ASGI app that is being wrapped.

    Returns:
        A wrapped ASGIApp.
    """
    from litestar.middleware.exceptions import ExceptionHandlerMiddleware

    return ExceptionHandlerMiddleware(app=app, debug=None)


def get_route_handlers(route: BaseRoute) -> list[RouteHandlerType]:
    """Retrieve handler(s) as a list for given route.

    Args:
        route: The route from which the route handlers are extracted.

    Returns:
        The route handlers defined on the route.
    """
    route_handlers: list[RouteHandlerType] = []
    if hasattr(route, "route_handlers"):
        route_handlers.extend(cast("HTTPRoute", route).route_handlers)
    else:
        route_handlers.append(cast("WebSocketRoute | ASGIRoute", route).route_handler)

    return route_handlers
