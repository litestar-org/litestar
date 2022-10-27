from typing import TYPE_CHECKING, List, cast

if TYPE_CHECKING:
    from typing import Union

    from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from starlite.routes.base import BaseRoute
    from starlite.types import ASGIApp, ExceptionHandlersMap, RouteHandlerType


def wrap_in_exception_handler(debug: bool, app: "ASGIApp", exception_handlers: "ExceptionHandlersMap") -> "ASGIApp":
    """Wraps the given ASGIApp in an instance of ExceptionHandlerMiddleware."""
    from starlite.middleware.exceptions import ExceptionHandlerMiddleware

    return ExceptionHandlerMiddleware(app=app, exception_handlers=exception_handlers, debug=debug)


def get_route_handlers(route: "BaseRoute") -> List["RouteHandlerType"]:
    """Retrieve handler(s) as a list for given route."""
    route_handlers: List["RouteHandlerType"] = []
    if hasattr(route, "route_handlers"):
        route_handlers.extend(cast("HTTPRoute", route).route_handlers)
    else:
        route_handlers.append(cast("Union[WebSocketRoute, ASGIRoute]", route).route_handler)

    return route_handlers
