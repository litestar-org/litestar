import collections
from typing import TYPE_CHECKING, Dict, ItemsView, List, Optional, Type, Union, cast

from pydantic import validate_arguments
from pydantic_openapi_schema.v3_1_0 import SecurityRequirement

from starlite.controller import Controller
from starlite.datastructures.provide import Provide
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers import (
    ASGIRouteHandler,
    BaseRouteHandler,
    HTTPRouteHandler,
    WebsocketRouteHandler,
)
from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
from starlite.types import (
    AfterRequestHookHandler,
    AfterResponseHookHandler,
    BeforeRequestHookHandler,
    ControllerRouterHandler,
    ExceptionHandler,
    Guard,
    Middleware,
    ParametersMap,
    ResponseCookies,
    ResponseHeadersMap,
    ResponseType,
    RouteHandlerMapItem,
)
from starlite.utils import (
    find_index,
    is_class_and_subclass,
    join_paths,
    normalize_path,
    unique,
)
from starlite.utils.sync import AsyncCallable

if TYPE_CHECKING:
    from starlite.routes import BaseRoute


class Router:
    __slots__ = (
        "after_request",
        "before_request",
        "after_response",
        "dependencies",
        "exception_handlers",
        "guards",
        "middleware",
        "owner",
        "parameters",
        "path",
        "response_class",
        "response_cookies",
        "response_headers",
        "routes",
        "security",
        "tags",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: str,
        *,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Middleware]] = None,
        parameters: Optional[ParametersMap] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        route_handlers: List[ControllerRouterHandler],
        security: Optional[List[SecurityRequirement]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """The Starlite Router class.

        A Router instance is used to group controller, routers and route handler functions under a shared path fragment.

        Args:
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            middleware: A list of [Middleware][starlite.types.Middleware].
            parameters: A mapping of [Parameter][starlite.params.Parameter] definitions available to all
                application paths.
            path: A path fragment that is prefixed to all route handlers, controllers and other routers associated
                with the router instance.
            response_class: A custom subclass of [starlite.response.Response] to be used as the default for all route
                handlers, controllers and other routers associated with the router instance.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            route_handlers: A required list of route handlers, which can include instances of
                [Router][starlite.router.Router], subclasses of [Controller][starlite.controller.Controller] or any
                function decorated by the route handler decorators.
            security: A list of dictionaries that will be added to the schema of all route handlers under the router.
            tags: A list of string tags that will be appended to the schema of all route handlers under the router.
        """
        self.after_request = AsyncCallable(after_request) if after_request else None  # type: ignore[arg-type]
        self.after_response = AsyncCallable(after_response) if after_response else None
        self.before_request = AsyncCallable(before_request) if before_request else None
        self.dependencies = dependencies or {}
        self.exception_handlers = exception_handlers or {}
        self.guards = guards or []
        self.middleware = middleware or []
        self.owner: Optional["Router"] = None
        self.parameters = parameters or {}
        self.path = normalize_path(path)
        self.response_class = response_class
        self.response_cookies = response_cookies or []
        self.response_headers = response_headers or {}
        self.routes: List["BaseRoute"] = []
        self.security = security or []
        self.tags = tags or []

        for route_handler in route_handlers or []:
            self.register(value=route_handler)

    def register(self, value: ControllerRouterHandler) -> List["BaseRoute"]:
        """Register a Controller, Route instance or RouteHandler on the router.

        Args:
            value: a subclass or instance of Controller, an instance of `Router` or a function/method that has been
                decorated by any of the routing decorators, e.g. [get][starlite.handlers.http.get],
                [post][starlite.handlers.http.post].

        Returns:
            Collection of handlers added to the router.
        """
        validated_value = self._validate_registration_value(value)
        routes: List["BaseRoute"] = []
        for route_path, handler_or_method_map in self._map_route_handlers(value=validated_value):
            path = join_paths([self.path, route_path])
            if isinstance(handler_or_method_map, WebsocketRouteHandler):
                route: "BaseRoute" = WebSocketRoute(path=path, route_handler=handler_or_method_map)
                self.routes.append(route)
            elif isinstance(handler_or_method_map, ASGIRouteHandler):
                route = ASGIRoute(path=path, route_handler=handler_or_method_map)
                self.routes.append(route)
            else:
                existing_handlers: List[HTTPRouteHandler] = list(self.route_handler_method_map.get(path, {}).values())  # type: ignore
                route_handlers = unique(list(handler_or_method_map.values()))
                if existing_handlers:
                    route_handlers.extend(unique(existing_handlers))
                    existing_route_index = find_index(
                        self.routes, lambda x: x.path == path  # pylint: disable=cell-var-from-loop
                    )
                    assert existing_route_index != -1, "unable to find_index existing route index"
                    route = HTTPRoute(
                        path=path,
                        route_handlers=route_handlers,
                    )
                    self.routes[existing_route_index] = route
                else:
                    route = HTTPRoute(path=path, route_handlers=route_handlers)
                    self.routes.append(route)
            routes.append(route)
        return routes

    @property
    def route_handler_method_map(self) -> Dict[str, RouteHandlerMapItem]:
        """
        Returns:
             A dictionary mapping paths to route handlers
        """
        route_map: Dict[str, RouteHandlerMapItem] = collections.defaultdict(dict)
        for route in self.routes:
            if isinstance(route, HTTPRoute):
                for route_handler in route.route_handlers:
                    for method in route_handler.http_methods:
                        route_map[route.path][method] = route_handler  # type: ignore
            else:
                route_map[route.path] = cast("WebSocketRoute", route).route_handler
        return route_map

    @classmethod
    def _map_route_handlers(
        cls,
        value: Union[Controller, BaseRouteHandler, "Router"],
    ) -> ItemsView[str, RouteHandlerMapItem]:
        """Maps route handlers to HTTP methods."""
        if isinstance(value, Router):
            return value.route_handler_method_map.items()
        if isinstance(value, BaseRouteHandler):
            return cls._map_route_handlers_for_base_route_handler(value)
        # we are dealing with a controller
        return cls._map_route_handlers_for_controller(value)

    @staticmethod
    def _map_route_handlers_for_base_route_handler(value: BaseRouteHandler) -> ItemsView[str, RouteHandlerMapItem]:
        """Maps route handlers to HTTP methods for an input
        BaseRouteHandler."""
        handlers_map: Dict[str, RouteHandlerMapItem] = {}
        for path in value.paths:
            if isinstance(value, HTTPRouteHandler):
                handlers_map[path] = {http_method: value for http_method in value.http_methods}
            elif isinstance(value, (WebsocketRouteHandler, ASGIRouteHandler)):
                handlers_map[path] = value
        return handlers_map.items()

    @classmethod
    def _map_route_handlers_for_controller(cls, value: Controller) -> ItemsView[str, RouteHandlerMapItem]:
        """Maps route handlers to HTTP methods for an input Controller."""
        handlers_map: Dict[str, RouteHandlerMapItem] = {}
        for route_handler in value.get_route_handlers():
            for handler_path in route_handler.paths:
                path = join_paths([value.path, handler_path]) if handler_path else value.path
                if isinstance(route_handler, HTTPRouteHandler):
                    handlers_map[path] = cls._create_http_handler_item(handlers_map, route_handler, path)
                else:
                    handlers_map[path] = cast("Union[WebsocketRouteHandler, ASGIRouteHandler]", route_handler)
        return handlers_map.items()

    @staticmethod
    def _create_http_handler_item(
        handlers_map: Dict[str, RouteHandlerMapItem], route_handler: HTTPRouteHandler, path: str
    ) -> RouteHandlerMapItem:
        """Creates a dict of HTTP method to route handler for a single
        controller path."""
        handler_item: Optional[RouteHandlerMapItem] = handlers_map.get(path)
        if not isinstance(handler_item, dict):
            handler_item = {}
        for http_method in route_handler.http_methods:
            handler_item[http_method] = route_handler
        return handler_item

    def _validate_registration_value(
        self, value: ControllerRouterHandler
    ) -> Union[Controller, BaseRouteHandler, "Router"]:
        """Validates that the value passed to the register method is
        supported."""
        if is_class_and_subclass(value, Controller):
            return value(owner=self)
        if not isinstance(value, (Router, BaseRouteHandler)):
            raise ImproperlyConfiguredException(
                "Unsupported value passed to `Router.register`. "
                "If you passed in a function or method, "
                "make sure to decorate it first with one of the routing decorators"
            )
        if isinstance(value, Router):
            if value.owner:
                raise ImproperlyConfiguredException(f"Router with path {value.path} has already been registered")
            if value is self:
                raise ImproperlyConfiguredException("Cannot register a router on itself")
        value.owner = self
        return cast("Union[Controller, BaseRouteHandler, Router]", value)
