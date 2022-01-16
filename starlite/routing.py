import re
from abc import ABC
from inspect import isclass
from typing import Any, Dict, ItemsView, List, Optional, Tuple, Union, cast

from pydantic import validate_arguments
from pydantic.typing import AnyCallable
from starlette.datastructures import URLPath
from starlette.routing import BaseRoute as StarletteBaseRoute
from starlette.routing import (
    Match,
    NoMatchFound,
    compile_path,
    get_name,
    replace_params,
)
from starlette.types import Receive, Scope, Send
from typing_extensions import Type

from starlite.controller import Controller
from starlite.enums import HttpMethod, ScopeType
from starlite.exceptions import ImproperlyConfiguredException, MethodNotAllowedException
from starlite.handlers import BaseRouteHandler, HTTPRouteHandler, WebsocketRouteHandler
from starlite.provide import Provide
from starlite.request import Request, WebSocket
from starlite.response import Response
from starlite.types import ControllerRouterHandler, Guard, Method, ResponseHeader
from starlite.utils import find_index, join_paths, normalize_path, unique

param_match_regex = re.compile(r"{(.*?)}")


class BaseRoute(ABC, StarletteBaseRoute):
    __slots__ = (
        "app",
        "handler_names",
        "methods",
        "param_convertors",
        "path",
        "path_format",
        "path_parameters",
        "path_regex",
        "scope_type",
    )

    @validate_arguments()
    def __init__(
        self,
        *,
        handler_names: List[str],
        path: str,
        scope_type: ScopeType,
        methods: Optional[List[Method]] = None,
    ):
        if not path.startswith("/"):
            raise ImproperlyConfiguredException("Routed paths must start with '/'")
        self.handler_names = handler_names
        self.path = path
        self.scope_type = scope_type
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)
        self.path_parameters: List[str] = param_match_regex.findall(self.path)

        self.methods = methods or []
        if "GET" in self.methods:
            self.methods.append("HEAD")
        for parameter in self.path_parameters:
            if ":" not in parameter or not parameter.split(":")[1]:
                raise ImproperlyConfiguredException("path parameter must declare a type: '{parameter_name:type}'")

    @property
    def is_http_route(self) -> bool:
        """Determines whether the given route is an http or websocket route"""
        return self.scope_type == "http"

    def matches(self, scope: Scope) -> Tuple[Match, Scope]:
        """
        Try to match a given scope's path to self.path
        """
        if scope["type"] == self.scope_type.value:
            match = self.path_regex.match(scope["path"])
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {"endpoint": self, "path_params": path_params}
                if self.is_http_route and scope["method"] not in self.methods:
                    return Match.PARTIAL, child_scope
                return Match.FULL, child_scope
        return Match.NONE, {}

    def url_path_for(self, name: str, **path_params: str) -> URLPath:
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if name not in self.handler_names or seen_params != expected_params:
            raise NoMatchFound()

        path, remaining_params = replace_params(self.path_format, self.param_convertors, path_params)
        assert not remaining_params
        return URLPath(path=path, protocol=self.scope_type.value)


class HTTPRoute(BaseRoute):
    __slots__ = (
        "app",
        "handler_names",
        "methods",
        "param_convertors",
        "path",
        "path_format",
        "path_parameters",
        "path_regex",
        "route_handler_map",
        "scope_type",
    )

    @validate_arguments()
    def __init__(
        self,
        *,
        path: str,
        route_handlers: Union[HTTPRouteHandler, List[HTTPRouteHandler]],
    ):
        route_handlers = route_handlers if isinstance(route_handlers, list) else [route_handlers]
        self.route_handler_map = self.parse_route_handlers(route_handlers=route_handlers, path=path)
        super().__init__(
            methods=[method.to_str() for method in self.route_handler_map],
            path=path,
            scope_type=ScopeType.HTTP,
            handler_names=[get_name(cast(AnyCallable, route_handler.fn)) for route_handler in route_handlers],
        )

    @staticmethod
    def parse_route_handlers(route_handlers: List[HTTPRouteHandler], path: str) -> Dict[HttpMethod, HTTPRouteHandler]:
        """
        Parses the passed in route_handlers and returns a mapping of http-methods and route handlers
        """
        mapped_route_handlers: Dict[HttpMethod, HTTPRouteHandler] = {}
        for route_handler in route_handlers:
            for http_method in route_handler.http_methods:
                if mapped_route_handlers.get(http_method):
                    raise ImproperlyConfiguredException(
                        f"handler already registered for path {path!r} and http method {http_method}"
                    )
                mapped_route_handlers[http_method] = route_handler
        return mapped_route_handlers

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI app that creates a Request from the passed in args, and then awaits a Response
        """
        if scope["method"] not in self.methods:
            raise MethodNotAllowedException()
        request: Request[Any, Any] = Request(scope=scope, receive=receive, send=send)
        request_method = HttpMethod.from_str(request.method)
        handler = self.route_handler_map[request_method]
        response = await handler.handle_request(request=request)
        await response(scope, receive, send)


class WebSocketRoute(BaseRoute):
    __slots__ = (
        "app",
        "handler_names",
        "methods",
        "param_convertors",
        "path",
        "path_format",
        "path_parameters",
        "path_regex",
        "route_handler",
        "scope_type",
    )

    @validate_arguments()
    def __init__(
        self,
        *,
        path: str,
        route_handler: WebsocketRouteHandler,
    ):
        self.route_handler = route_handler
        super().__init__(
            path=path,
            scope_type=ScopeType.WEBSOCKET,
            handler_names=[get_name(cast(AnyCallable, route_handler.fn))],
        )

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI app that creates a WebSocket from the passed in args, and then awaits the handler function
        """
        web_socket: WebSocket[Any, Any] = WebSocket(scope=scope, receive=receive, send=send)
        await self.route_handler.handle_websocket(web_socket=web_socket)


class Router:
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        path: str,
        route_handlers: List[ControllerRouterHandler],
        dependencies: Optional[Dict[str, Provide]] = None,
        guards: Optional[List[Guard]] = None,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
    ):
        self.owner: Optional["Router"] = None
        self.routes: List[BaseRoute] = []
        self.path = normalize_path(path)
        self.response_class = response_class
        self.dependencies = dependencies
        self.response_headers = response_headers
        self.guards = guards
        for route_handler in route_handlers or []:
            self.register(value=route_handler)

    @property
    def route_handler_method_map(self) -> Dict[str, Union[WebsocketRouteHandler, Dict[HttpMethod, HTTPRouteHandler]]]:
        """
        Returns dictionary that maps paths (keys) to a list of route handler functions (values)
        """
        route_map: Dict[str, Union[WebsocketRouteHandler, Dict[HttpMethod, HTTPRouteHandler]]] = {}
        for route in self.routes:
            if isinstance(route, HTTPRoute):
                if not isinstance(route_map.get(route.path), dict):
                    route_map[route.path] = {}
                for method, handler in route.route_handler_map.items():
                    route_map[route.path][method] = handler  # type: ignore
            else:
                route_map[route.path] = cast(WebSocketRoute, route).route_handler
        return route_map

    @staticmethod
    def map_route_handlers(
        value: Union[Controller, BaseRouteHandler, "Router"],
    ) -> ItemsView[str, Union[WebsocketRouteHandler, Dict[HttpMethod, HTTPRouteHandler]]]:
        """
        Maps route handlers to http methods
        """
        handlers_map: Dict[str, Union[WebsocketRouteHandler, Dict[HttpMethod, HTTPRouteHandler]]] = {}
        if isinstance(value, BaseRouteHandler):
            if isinstance(value, HTTPRouteHandler):
                handlers_map[value.path or ""] = {http_method: value for http_method in value.http_methods}
            elif isinstance(value, WebsocketRouteHandler):
                handlers_map[value.path or ""] = value
        elif isinstance(value, Router):
            handlers_map = value.route_handler_method_map
        else:
            # we are dealing with a controller
            for route_handler in value.get_route_handlers():
                path = join_paths([value.path, route_handler.path]) if route_handler.path else value.path
                if isinstance(route_handler, HTTPRouteHandler):
                    if not isinstance(handlers_map.get(path), dict):
                        handlers_map[path] = {}
                    for http_method in route_handler.http_methods:
                        handlers_map[path][http_method] = route_handler  # type: ignore
                else:
                    handlers_map[path] = cast(WebsocketRouteHandler, route_handler)
        return handlers_map.items()

    def validate_registration_value(
        self, value: ControllerRouterHandler
    ) -> Union[Controller, BaseRouteHandler, "Router"]:
        """
        Validates that the value passed to the register method is supported
        """
        if isclass(value) and issubclass(cast(Type[Controller], value), Controller):
            return cast(Type[Controller], value)(owner=self)
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
        else:
            # the route handler is copied to ensure each time the route handler is registerd,
            # we get an instance with a unique owner
            value = value.copy()
        value.owner = self
        return cast(Union[Controller, BaseRouteHandler, "Router"], value)

    def register(self, value: ControllerRouterHandler) -> List[Union[HTTPRouteHandler, WebsocketRouteHandler]]:
        """
        Register a Controller, Route instance or RouteHandler on the router

        Accepts a subclass or instance of Controller, an instance of Router or a function/method that has been decorated
        by any of the routing decorators (e.g. route, get, post...) exported from 'starlite.routing'
        """
        validated_value = self.validate_registration_value(value)
        handlers: List[Union[HTTPRouteHandler, WebsocketRouteHandler]] = []
        for route_path, handler_or_method_map in self.map_route_handlers(value=validated_value):
            path = join_paths([self.path, route_path])
            if isinstance(handler_or_method_map, WebsocketRouteHandler):
                handlers.append(handler_or_method_map)
                self.routes.append(WebSocketRoute(path=path, route_handler=handler_or_method_map))
            else:
                route_handlers = list(handler_or_method_map.values())
                handlers.extend(route_handlers)
                if self.route_handler_method_map.get(path):
                    existing_route_index = find_index(
                        self.routes, lambda x: x.path == path  # pylint: disable=cell-var-from-loop
                    )
                    assert existing_route_index != -1, "unable to find_index existing route index"
                    if isinstance(self.route_handler_method_map[path], dict):
                        route_handlers.extend(list(cast(dict, self.route_handler_method_map[path]).values()))
                    self.routes[existing_route_index] = HTTPRoute(
                        path=path,
                        route_handlers=unique(route_handlers),
                    )
                else:
                    self.routes.append(HTTPRoute(path=path, route_handlers=unique(route_handlers)))
        return unique(handlers)
