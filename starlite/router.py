from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    ItemsView,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from pydantic import validate_arguments
from pydantic.fields import FieldInfo
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from starlite.controller import Controller
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers import (
    ASGIRouteHandler,
    BaseRouteHandler,
    HTTPRouteHandler,
    WebsocketRouteHandler,
)
from starlite.provide import Provide
from starlite.response import Response
from starlite.routes import ASGIRoute, BaseRoute, HTTPRoute, WebSocketRoute
from starlite.types import (
    AfterRequestHandler,
    AfterResponseHandler,
    BeforeRequestHandler,
    ControllerRouterHandler,
    ExceptionHandler,
    Guard,
    MiddlewareProtocol,
    ResponseHeader,
)
from starlite.utils import find_index, join_paths, normalize_path, unique

if TYPE_CHECKING:
    from starlite.enums import HttpMethod


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
        "response_headers",
        "routes",
        "tags",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]] = None,
        parameters: Optional[Dict[str, FieldInfo]] = None,
        path: str,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
        route_handlers: List[ControllerRouterHandler],
        tags: Optional[List[str]] = None,
    ):
        self.after_request = after_request
        self.after_response = after_response
        self.before_request = before_request
        self.dependencies = dependencies
        self.exception_handlers = exception_handlers
        self.guards = guards
        self.middleware = middleware
        self.owner: Optional["Router"] = None
        self.parameters = parameters
        self.path = normalize_path(path)
        self.response_class = response_class
        self.response_headers = response_headers
        self.routes: List[BaseRoute] = []
        self.tags = tags

        for route_handler in route_handlers or []:
            self.register(value=route_handler)

    @property
    def route_handler_method_map(self) -> Dict[str, Union[WebsocketRouteHandler, Dict["HttpMethod", HTTPRouteHandler]]]:
        """
        Returns dictionary that maps paths (keys) to a list of route handler functions (values)
        """
        route_map: Dict[str, Union[WebsocketRouteHandler, Dict["HttpMethod", HTTPRouteHandler]]] = {}
        for route in self.routes:
            if isinstance(route, HTTPRoute):
                if not isinstance(route_map.get(route.path), dict):
                    route_map[route.path] = {}
                for route_handler in route.route_handlers:
                    for method in route_handler.http_methods:
                        route_map[route.path][method] = route_handler  # type: ignore
            else:
                route_map[route.path] = cast("WebSocketRoute", route).route_handler
        return route_map

    @staticmethod
    def map_route_handlers(
        value: Union[Controller, BaseRouteHandler, "Router"],
    ) -> ItemsView[str, Union[WebsocketRouteHandler, ASGIRoute, Dict["HttpMethod", HTTPRouteHandler]]]:
        """
        Maps route handlers to http methods
        """
        handlers_map: Dict[str, Any] = {}
        if isinstance(value, BaseRouteHandler):
            for path in value.paths:
                if isinstance(value, HTTPRouteHandler):
                    handlers_map[path] = {http_method: value for http_method in value.http_methods}
                elif isinstance(value, (WebsocketRouteHandler, ASGIRouteHandler)):
                    handlers_map[path] = value
        elif isinstance(value, Router):
            handlers_map = value.route_handler_method_map
        else:
            # we are dealing with a controller
            for route_handler in value.get_route_handlers():
                for handler_path in route_handler.paths:
                    path = join_paths([value.path, handler_path]) if handler_path else value.path
                    if isinstance(route_handler, HTTPRouteHandler):
                        if not isinstance(handlers_map.get(path), dict):
                            handlers_map[path] = {}
                        for http_method in route_handler.http_methods:
                            handlers_map[path][http_method] = route_handler
                    else:
                        handlers_map[path] = cast("Union[WebsocketRouteHandler, ASGIRouteHandler]", route_handler)
        return handlers_map.items()

    def validate_registration_value(
        self, value: ControllerRouterHandler
    ) -> Union[Controller, BaseRouteHandler, "Router"]:
        """
        Validates that the value passed to the register method is supported
        """
        if isclass(value) and issubclass(cast("Type[Controller]", value), Controller):
            return cast("Type[Controller]", value)(owner=self)
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

    def register(self, value: ControllerRouterHandler) -> List[BaseRoute]:
        """
        Register a Controller, Route instance or RouteHandler on the router

        Accepts a subclass or instance of Controller, an instance of Router or a function/method that has been decorated
        by any of the routing decorators (e.g. route, get, post...) exported from 'starlite.routing'
        """
        validated_value = self.validate_registration_value(value)
        routes: List[BaseRoute] = []
        for route_path, handler_or_method_map in self.map_route_handlers(value=validated_value):
            path = join_paths([self.path, route_path])
            if isinstance(handler_or_method_map, WebsocketRouteHandler):
                route: BaseRoute = WebSocketRoute(path=path, route_handler=handler_or_method_map)
                self.routes.append(route)
            elif isinstance(handler_or_method_map, ASGIRouteHandler):
                route = ASGIRoute(path=path, route_handler=handler_or_method_map)
                self.routes.append(route)
            else:
                existing_handlers: List[HTTPRouteHandler] = list(self.route_handler_method_map.get(path, {}).values())  # type: ignore
                route_handlers = unique(
                    list(cast("Dict[HttpMethod, HTTPRouteHandler]", handler_or_method_map).values())
                )
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
