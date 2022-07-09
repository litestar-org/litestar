from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, cast

from starlite.handlers import BaseRouteHandler
from starlite.utils import normalize_path

if TYPE_CHECKING:  # pragma: no cover
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from typing_extensions import Type

    from starlite.provide import Provide
    from starlite.response import Response
    from starlite.router import Router
    from starlite.types import (
        AfterRequestHandler,
        BeforeRequestHandler,
        ExceptionHandler,
        Guard,
        MiddlewareProtocol,
        ResponseHeader,
    )


class Controller:
    """
    Starlite Controller. This is the basic 'view' component of Starlite.
    """

    __slots__ = (
        "after_request",
        "before_request",
        "dependencies",
        "exception_handlers",
        "guards",
        "middleware",
        "owner",
        "path",
        "response_class",
        "response_headers",
        "tags",
    )

    after_request: AfterRequestHandler | None
    before_request: BeforeRequestHandler | None
    dependencies: dict[str, Provide] | None
    exception_handlers: dict[int | Type[Exception], ExceptionHandler] | None
    guards: list[Guard] | None
    middleware: list[Middleware | Type[BaseHTTPMiddleware] | Type[MiddlewareProtocol]] | None
    owner: Router
    path: str
    response_class: Type[Response] | None
    response_headers: dict[str, ResponseHeader] | None
    tags: list[str] | None

    def __init__(self, owner: Router):
        for key in [
            "after_request",
            "before_request",
            "dependencies",
            "exception_handlers",
            "guards",
            "middleware",
            "response_class",
            "response_headers",
        ]:
            if not hasattr(self, key):
                setattr(self, key, None)

        self.path = normalize_path(self.path or "/")
        self.owner = owner

    def get_route_handlers(self) -> list[BaseRouteHandler]:
        """
        Returns a list of route handlers defined on the controller
        """
        route_handlers: list[BaseRouteHandler] = []
        route_handler_fields = [
            f_name
            for f_name in dir(self)
            if f_name not in dir(Controller) and isinstance(getattr(self, f_name), BaseRouteHandler)
        ]
        for f_name in route_handler_fields:
            source_route_handler = cast(BaseRouteHandler, getattr(self, f_name))
            route_handler = copy(source_route_handler)
            route_handler.owner = self
            route_handlers.append(route_handler)
        return route_handlers
