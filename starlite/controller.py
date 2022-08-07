import inspect
from copy import copy
from typing import TYPE_CHECKING, Dict, List, Optional, Union, cast

from starlite.handlers import BaseRouteHandler
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from typing import Type

    from pydantic.fields import FieldInfo
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware

    from starlite.provide import Provide
    from starlite.response import Response
    from starlite.router import Router
    from starlite.types import (
        AfterRequestHandler,
        AfterResponseHandler,
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
        "after_response",
        "before_request",
        "dependencies",
        "exception_handlers",
        "guards",
        "middleware",
        "owner",
        "parameters",
        "path",
        "response_class",
        "response_headers",
        "tags",
    )

    after_request: Optional["AfterRequestHandler"]
    after_response: Optional["AfterResponseHandler"]
    before_request: Optional["BeforeRequestHandler"]
    dependencies: Optional[Dict[str, "Provide"]]
    exception_handlers: Optional[Dict[Union[int, "Type[Exception]"], "ExceptionHandler"]]
    guards: Optional[List["Guard"]]
    middleware: Optional[List[Union["Middleware", "Type[BaseHTTPMiddleware]", "Type[MiddlewareProtocol]"]]]
    owner: "Router"
    parameters: Optional[Dict[str, "FieldInfo"]]
    path: str
    response_class: Optional["Type[Response]"]
    response_headers: Optional[Dict[str, "ResponseHeader"]]
    tags: Optional[List[str]]

    def __init__(self, owner: "Router"):
        for key in self.__slots__:
            if not hasattr(self, key):
                setattr(self, key, None)

        self.path = normalize_path(self.path or "/")
        self.owner = owner
        self._unbind_lifecycle_hook_functions()

    def _unbind_lifecycle_hook_functions(self) -> None:
        """
        Functions assigned to class variables will be bound as instance methods on instantiation of the controller.
        Left unchecked, this results in a `TypeError` when the handlers are called as any function satisfying the type
        annotation of the lifecycle hook attributes can only receive a single positional argument, but will receive two
        positional arguments if called as an instance method (`self` and the hook argument)`.

        Overwrites the bound method with the original function.
        """
        for hook_key in ("after_request", "after_response", "before_request"):
            hook_class_var = getattr(type(self), hook_key, None)
            if not hook_class_var:
                continue
            if inspect.isfunction(hook_class_var):
                setattr(self, hook_key, hook_class_var)

    def get_route_handlers(self) -> List["BaseRouteHandler"]:
        """
        Returns a list of route handlers defined on the controller
        """
        route_handlers: List["BaseRouteHandler"] = []
        route_handler_fields = [
            f_name
            for f_name in dir(self)
            if f_name not in dir(Controller) and isinstance(getattr(self, f_name), BaseRouteHandler)
        ]
        for f_name in route_handler_fields:
            source_route_handler = cast("BaseRouteHandler", getattr(self, f_name))
            route_handler = copy(source_route_handler)
            route_handler.owner = self
            route_handlers.append(route_handler)
        return route_handlers
