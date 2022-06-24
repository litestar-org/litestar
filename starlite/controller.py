from copy import copy
from typing import TYPE_CHECKING, Dict, List, Optional, Union, cast

from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing_extensions import Type

from starlite.handlers import BaseRouteHandler
from starlite.response import Response
from starlite.types import (
    AfterRequestHandler,
    BeforeRequestHandler,
    ExceptionHandler,
    Guard,
    MiddlewareProtocol,
    ResponseHeader,
)
from starlite.utils import normalize_path

if TYPE_CHECKING:  # pragma: no cover
    from starlite.provide import Provide
    from starlite.router import Router


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

    after_request: Optional[AfterRequestHandler]
    before_request: Optional[BeforeRequestHandler]
    dependencies: Optional[Dict[str, "Provide"]]
    exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]]
    guards: Optional[List[Guard]]
    middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]]
    owner: "Router"
    path: str
    response_class: Optional[Type[Response]]
    response_headers: Optional[Dict[str, ResponseHeader]]
    tags: Optional[List[str]]

    def __init__(self, owner: "Router"):
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

    def get_route_handlers(self) -> List[BaseRouteHandler]:
        """
        Returns a list of route handlers defined on the controller
        """
        route_handlers: List[BaseRouteHandler] = []
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
