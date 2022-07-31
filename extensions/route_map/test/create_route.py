from typing import Any, Callable

from starlite import BaseRoute, HTTPRouteHandler, Starlite
from starlite.handlers import http


def http_route(path: str, method: str) -> BaseRoute:
    annotation: Callable[[Callable[..., Any]], HTTPRouteHandler] = getattr(http, method)(path)

    @annotation
    def handler_fn(**kwargs: Any) -> None:
        ...

    app = Starlite(route_handlers=[handler_fn])
    route = app.routes[0]
    return route
