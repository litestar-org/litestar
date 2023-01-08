from copy import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from starlite.handlers import BaseRouteHandler
from starlite.utils import AsyncCallable, normalize_path
from starlite.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from pydantic_openapi_schema.v3_1_0 import SecurityRequirement

    from starlite.datastructures import CacheControlHeader, ETag
    from starlite.router import Router
    from starlite.types import (
        AfterRequestHookHandler,
        AfterResponseHookHandler,
        BeforeRequestHookHandler,
        Dependencies,
        ExceptionHandlersMap,
        Guard,
        Middleware,
        ParametersMap,
        ResponseCookies,
        ResponseHeadersMap,
        ResponseType,
        TypeEncodersMap,
    )


class Controller:
    """The Starlite Controller class.

    Subclass this class to create 'view' like components and utilize OOP.
    """

    __slots__ = (
        "after_request",
        "after_response",
        "before_request",
        "dependencies",
        "etag",
        "exception_handlers",
        "guards",
        "middleware",
        "opt",
        "owner",
        "parameters",
        "path",
        "response_class",
        "response_cookies",
        "response_headers",
        "security",
        "tags",
        "type_encoders",
    )

    after_request: Optional["AfterRequestHookHandler"]
    """A sync or async function executed before a [Request][starlite.connection.Request] is passed to any route handler.

    If this function returns a value, the request will not reach the route handler, and instead this value will be used.
    """
    after_response: Optional["AfterResponseHookHandler"]
    """A sync or async function called after the response has been awaited.

    It receives the [Request][starlite.connection.Request] instance and should not return any values.
    """
    before_request: Optional["BeforeRequestHookHandler"]
    """A sync or async function called immediately before calling the route handler.

    It receives the [Request][starlite.connection.Request] instance and any non-`None` return value is used for the
    response, bypassing the route handler.
    """
    cache_control: Optional["CacheControlHeader"]
    """A [CacheControlHeader][starlite.datastructures.CacheControlHeader] header to add to route handlers of this
    controller.

    Can be overridden by route handlers.
    """
    dependencies: Optional["Dependencies"]
    """
        dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
    """
    etag: Optional["ETag"]
    """An `etag` header of type [ETag][starlite.datastructures.ETag] to add to route handlers of this controller.

    Can be overridden by route handlers.
    """
    exception_handlers: Optional["ExceptionHandlersMap"]
    """A dictionary that maps handler functions to status codes and/or exception types."""
    guards: Optional[List["Guard"]]
    """A list of [Guard][starlite.types.Guard] callables."""
    middleware: Optional[List["Middleware"]]
    """A list of [Middleware][starlite.types.Middleware]."""
    opt: Optional[Dict[str, Any]]
    """A string key dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or wherever
    you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
    """
    owner: "Router"
    """The [Router][starlite.router.Router] or [Starlite][starlite.app.Starlite] app that owns the controller.

    This value is set internally by Starlite and it should not be set when subclassing the controller.
    """
    parameters: Optional["ParametersMap"]
    """A mapping of [Parameter][starlite.params.Parameter] definitions available to all application paths."""
    path: str
    """A path fragment for the controller.

    All route handlers under the controller will have the fragment appended to them. If not set it defaults to '/'.
    """
    response_class: Optional["ResponseType"]
    """A custom subclass of [starlite.response.Response] to be used as the default response for all route handlers under
    the controller.
    """
    response_cookies: Optional["ResponseCookies"]
    """A list of [Cookie](starlite.datastructures.Cookie] instances."""
    response_headers: Optional["ResponseHeadersMap"]
    """A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader] instances."""
    tags: Optional[List[str]]
    """A list of string tags that will be appended to the schema of all route handlers under the controller."""
    security: Optional[List["SecurityRequirement"]]
    """A list of dictionaries that to the schema of all route handlers under the controller."""
    type_encoders: Optional["TypeEncodersMap"]
    """A mapping of types to callables that transform them into types supported for serialization."""

    def __init__(self, owner: "Router") -> None:
        """Initialize a controller.

        Should only be called by routers as part of controller registration.

        Args:
            owner: An instance of 'Router'
        """
        # Since functions set on classes are bound, we need replace the bound instance with the class version and wrap
        # it to ensure it does not get bound.
        for key in ("after_request", "after_response", "before_request"):
            cls_value = getattr(type(self), key, None)
            if callable(cls_value):
                setattr(self, key, AsyncCallable(cls_value))

        for key in self.__slots__:
            if not hasattr(self, key):
                setattr(self, key, None)

        self.path = normalize_path(self.path or "/")
        self.owner = owner

    def get_route_handlers(self) -> List["BaseRouteHandler"]:
        """Get a controller's route handlers and set the controller as the handlers' owner.

        Returns:
            A list containing a copy of the route handlers defined on the controller
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
            if hasattr(route_handler.fn.value, "func"):
                route_handler.fn.value = unwrap_partial(route_handler.fn.value)

            route_handler.owner = self
            route_handlers.append(route_handler)

        return route_handlers
