from __future__ import annotations

from collections import defaultdict
from copy import copy
from typing import TYPE_CHECKING, Any, DefaultDict, Mapping, cast

from litestar._layers.utils import narrow_response_cookies, narrow_response_headers
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers.base import BaseRouteHandler
from litestar.handlers.http_handlers import HTTPRouteHandler
from litestar.handlers.websocket_handlers import WebsocketRouteHandler
from litestar.types.empty import Empty
from litestar.utils import AsyncCallable, normalize_path
from litestar.utils.helpers import unwrap_partial

__all__ = ("Controller",)


if TYPE_CHECKING:
    from litestar.datastructures import CacheControlHeader, ETag
    from litestar.dto.interface import DTOInterface
    from litestar.openapi.spec import SecurityRequirement
    from litestar.response import Response
    from litestar.router import Router
    from litestar.types import (
        AfterRequestHookHandler,
        AfterResponseHookHandler,
        BeforeRequestHookHandler,
        Dependencies,
        ExceptionHandlersMap,
        Guard,
        Middleware,
        OptionalSequence,
        ParametersMap,
        ResponseCookies,
        TypeEncodersMap,
    )
    from litestar.types.composite_types import ResponseHeaders
    from litestar.types.empty import EmptyType


class Controller:
    """The Litestar Controller class.

    Subclass this class to create 'view' like components and utilize OOP.
    """

    __slots__ = (
        "after_request",
        "after_response",
        "before_request",
        "dependencies",
        "dto",
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
        "return_dto",
        "security",
        "signature_namespace",
        "tags",
        "type_encoders",
    )

    after_request: AfterRequestHookHandler | None
    """A sync or async function executed before a :class:`Request <.connection.Request>` is passed to any route handler.

    If this function returns a value, the request will not reach the route handler, and instead this value will be used.
    """
    after_response: AfterResponseHookHandler | None
    """A sync or async function called after the response has been awaited.

    It receives the :class:`Request <.connection.Request>` instance and should not return any values.
    """
    before_request: BeforeRequestHookHandler | None
    """A sync or async function called immediately before calling the route handler.

    It receives the :class:`Request <.connection.Request>` instance and any non-``None`` return value is used for the
    response, bypassing the route handler.
    """
    cache_control: CacheControlHeader | None
    """A :class:`CacheControlHeader <.datastructures.CacheControlHeader>` header to add to route handlers of this
    controller.

    Can be overridden by route handlers.
    """
    dependencies: Dependencies | None
    """A string keyed dictionary of dependency :class:`Provider <.di.Provide>` instances."""
    dto: type[DTOInterface] | None | EmptyType
    """:class:`DTOInterface <.dto.interface.DTOInterface>` to use for (de)serializing and validation of request data."""
    etag: ETag | None
    """An ``etag`` header of type :class:`ETag <.datastructures.ETag>` to add to route handlers of this controller.

    Can be overridden by route handlers.
    """
    exception_handlers: ExceptionHandlersMap | None
    """A map of handler functions to status codes and/or exception types."""
    guards: OptionalSequence[Guard]
    """A sequence of :class:`Guard <.types.Guard>` callables."""
    middleware: OptionalSequence[Middleware]
    """A sequence of :class:`Middleware <.types.Middleware>`."""
    opt: Mapping[str, Any] | None
    """A string key mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or wherever you
    have access to :class:`Request <.connection.Request>` or :class:`ASGI Scope <.types.Scope>`.
    """
    owner: Router
    """The :class:`Router <.router.Router>` or :class:`Litestar <litestar.app.Litestar>` app that owns the controller.

    This value is set internally by Litestar and it should not be set when subclassing the controller.
    """
    parameters: ParametersMap | None
    """A mapping of :class:`Parameter <.params.Parameter>` definitions available to all application paths."""
    path: str
    """A path fragment for the controller.

    All route handlers under the controller will have the fragment appended to them. If not set it defaults to ``/``.
    """
    response_class: type[Response] | None
    """A custom subclass of :class:`Response <.response.Response>` to be used as the default response for all route
    handlers under the controller.
    """
    response_cookies: ResponseCookies | None
    """A list of :class:`Cookie <.datastructures.Cookie>` instances."""
    response_headers: ResponseHeaders | None
    """A string keyed dictionary mapping :class:`ResponseHeader <.datastructures.ResponseHeader>` instances."""
    return_dto: type[DTOInterface] | None | EmptyType
    """:class:`DTOInterface <.dto.interface.DTOInterface>` to use for serializing outbound response
    data.
    """
    tags: OptionalSequence[str]
    """A sequence of string tags that will be appended to the schema of all route handlers under the controller."""
    security: OptionalSequence[SecurityRequirement]
    """A sequence of dictionaries that to the schema of all route handlers under the controller."""
    signature_namespace: dict[str, Any]
    """A mapping of names to types for use in forward reference resolution during signature modelling."""
    type_encoders: TypeEncodersMap | None
    """A mapping of types to callables that transform them into types supported for serialization."""

    def __init__(self, owner: Router) -> None:
        """Initialize a controller.

        Should only be called by routers as part of controller registration.

        Args:
            owner: An instance of :class:`Router <.router.Router>`
        """
        # Since functions set on classes are bound, we need replace the bound instance with the class version and wrap
        # it to ensure it does not get bound.
        for key in ("after_request", "after_response", "before_request"):
            cls_value = getattr(type(self), key, None)
            if callable(cls_value):
                setattr(self, key, AsyncCallable(cls_value))

        if not hasattr(self, "dto"):
            self.dto = Empty

        if not hasattr(self, "return_dto"):
            self.return_dto = Empty

        for key in self.__slots__:
            if not hasattr(self, key):
                setattr(self, key, None)

        self.response_cookies = narrow_response_cookies(self.response_cookies)
        self.response_headers = narrow_response_headers(self.response_headers)
        self.signature_namespace = self.signature_namespace or {}

        self.path = normalize_path(self.path or "/")
        self.owner = owner

    def get_route_handlers(self) -> list[BaseRouteHandler]:
        """Get a controller's route handlers and set the controller as the handlers' owner.

        Returns:
            A list containing a copy of the route handlers defined on the controller
        """
        route_handlers: list[BaseRouteHandler] = []
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

        self.validate_route_handlers(route_handlers=route_handlers)

        return route_handlers

    def validate_route_handlers(self, route_handlers: list[BaseRouteHandler]) -> None:
        """Validate that the combination of path and decorator method or type are unique on the controller.

        Args:
            route_handlers: The controller's route handlers.

        Raises:
            ImproperlyConfiguredException

        Returns:
            None
        """
        paths: DefaultDict[str, set[str]] = defaultdict(set)

        for route_handler in route_handlers:
            if isinstance(route_handler, HTTPRouteHandler):
                methods: set[str] = cast("set[str]", route_handler.http_methods)
            elif isinstance(route_handler, WebsocketRouteHandler):
                methods = {"websocket"}
            else:
                methods = {"asgi"}

            for path in route_handler.paths:
                if (entry := paths[path]) and (intersection := entry.intersection(methods)):
                    raise ImproperlyConfiguredException(
                        f"the combination of path and method must be unique in a controller - "
                        f"the following methods {''.join(m.lower() for m in intersection)} for {type(self).__name__} "
                        f"controller path {path} are not unique"
                    )
                paths[path].update(methods)
