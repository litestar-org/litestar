import re
from inspect import isawaitable, isclass
from itertools import chain
from typing import Any, Dict, ItemsView, List, Optional, Tuple, Union, cast
from uuid import UUID

from pydantic import validate_arguments
from pydantic.typing import AnyCallable
from starlette.requests import HTTPConnection
from starlette.routing import get_name
from starlette.types import Receive, Scope, Send
from typing_extensions import Type

from starlite.connection import Request, WebSocket
from starlite.controller import Controller
from starlite.enums import HttpMethod, ScopeType
from starlite.exceptions import ImproperlyConfiguredException, MethodNotAllowedException
from starlite.handlers import (
    ASGIRouteHandler,
    BaseRouteHandler,
    HTTPRouteHandler,
    WebsocketRouteHandler,
)
from starlite.kwargs import KwargsModel
from starlite.provide import Provide
from starlite.response import Response
from starlite.signature import get_signature_model
from starlite.types import (
    AfterRequestHandler,
    AsyncAnyCallable,
    BeforeRequestHandler,
    ControllerRouterHandler,
    Guard,
    Method,
    ResponseHeader,
)
from starlite.utils import find_index, join_paths, normalize_path, unique

param_match_regex = re.compile(r"{(.*?)}")


class BaseRoute:
    __slots__ = (
        "app",
        "handler_names",
        "methods",
        "param_convertors",
        "path",
        "path_format",
        "path_parameters",
        "scope_type",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        handler_names: List[str],
        path: str,
        scope_type: ScopeType,
        methods: Optional[List[Method]] = None,
    ):
        self.path, self.path_format, self.path_parameters = self.parse_path(path)
        self.handler_names = handler_names
        self.scope_type = scope_type
        self.methods = set(methods or [])
        if "GET" in self.methods:
            self.methods.add("HEAD")

    @staticmethod
    def parse_path(path: str) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        Normalizes and parses a path
        """
        path = normalize_path(path)
        path_format = path
        path_parameters = []

        param_type_map = {"str": str, "int": int, "float": float, "uuid": UUID}

        for param in param_match_regex.findall(path):
            if ":" not in param:
                raise ImproperlyConfiguredException(
                    "Path parameters should be declared with a type using the following pattern: '{parameter_name:type}', e.g. '/my-path/{my_param:int}'"
                )
            param_name, param_type = (p.strip() for p in param.split(":"))
            path_format = path_format.replace(param, param_name)
            path_parameters.append({"name": param_name, "type": param_type_map[param_type], "full": param})
        return path, path_format, path_parameters

    def create_handler_kwargs_model(self, route_handler: BaseRouteHandler) -> KwargsModel:
        """
        Method to create a KwargsModel for a given route handler
        """
        dependencies = route_handler.resolve_dependencies()
        signature_model = get_signature_model(route_handler)
        path_parameters = {p["name"] for p in self.path_parameters}
        return KwargsModel.create_for_signature_model(
            signature_model=signature_model, dependencies=dependencies, path_parameters=path_parameters
        )


class HTTPRoute(BaseRoute):
    __slots__ = (
        "route_handler_map",
        "route_handlers"
        # the rest of __slots__ are defined in BaseRoute and should not be duplicated
        # see: https://stackoverflow.com/questions/472000/usage-of-slots
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        path: str,
        route_handlers: List[HTTPRouteHandler],
    ):
        self.route_handlers = route_handlers
        self.route_handler_map: Dict[Method, Tuple[HTTPRouteHandler, KwargsModel]] = {}
        super().__init__(
            methods=list(chain.from_iterable([route_handler.http_methods for route_handler in route_handlers])),
            path=path,
            scope_type=ScopeType.HTTP,
            handler_names=[get_name(cast(AnyCallable, route_handler.fn)) for route_handler in route_handlers],
        )

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI app that creates a Request from the passed in args, and then awaits a Response
        """
        if scope["method"] not in self.methods:
            raise MethodNotAllowedException()
        request: Request[Any, Any] = Request(scope=scope, receive=receive, send=send)

        route_handler, parameter_model = self.route_handler_map[request.method]
        if route_handler.resolve_guards():
            await route_handler.authorize_connection(connection=request)
        response_data = None
        before_request_handler = route_handler.resolve_before_request()
        # run the before_request hook handler
        if before_request_handler:
            response_data = before_request_handler(request)
            if isawaitable(response_data):
                response_data = await response_data
        if not response_data:
            signature_model = get_signature_model(route_handler)
            if signature_model.has_kwargs:
                kwargs = parameter_model.to_kwargs(connection=request)
                request_data = kwargs.get("data")
                if request_data:
                    kwargs["data"] = await request_data
                for dependency in parameter_model.expected_dependencies:
                    kwargs[dependency.key] = await parameter_model.resolve_dependency(
                        dependency=dependency, connection=request, **kwargs
                    )
                parsed_kwargs = signature_model.parse_values_from_connection_kwargs(connection=request, **kwargs)
            else:
                parsed_kwargs = {}
            fn = cast(AnyCallable, route_handler.fn)
            if isinstance(route_handler.owner, Controller):
                response_data = fn(route_handler.owner, **parsed_kwargs)
            else:
                response_data = fn(**parsed_kwargs)
        response = await route_handler.to_response(
            app=scope["app"],
            data=response_data,
            plugins=request.app.plugins,
        )
        await response(scope, receive, send)

    def create_handler_map(self) -> None:
        """
        Parses the passed in route_handlers and returns a mapping of http-methods and route handlers
        """
        for route_handler in self.route_handlers:
            kwargs_model = self.create_handler_kwargs_model(route_handler=route_handler)
            for http_method in route_handler.http_methods:
                if self.route_handler_map.get(http_method):
                    raise ImproperlyConfiguredException(
                        f"Handler already registered for path {self.path!r} and http method {http_method}"
                    )
                self.route_handler_map[http_method] = (route_handler, kwargs_model)


class WebSocketRoute(BaseRoute):
    __slots__ = (
        "route_handler",
        "handler_parameter_model"
        # the rest of __slots__ are defined in BaseRoute and should not be duplicated
        # see: https://stackoverflow.com/questions/472000/usage-of-slots
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        path: str,
        route_handler: WebsocketRouteHandler,
    ):
        self.route_handler = route_handler
        self.handler_parameter_model: Optional[KwargsModel] = None
        super().__init__(
            path=path,
            scope_type=ScopeType.WEBSOCKET,
            handler_names=[get_name(cast(AnyCallable, route_handler.fn))],
        )

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI app that creates a WebSocket from the passed in args, and then awaits the handler function
        """
        assert self.handler_parameter_model, "handler parameter model not defined"
        route_handler = self.route_handler
        web_socket: WebSocket[Any, Any] = WebSocket(scope=scope, receive=receive, send=send)
        if route_handler.resolve_guards():
            await route_handler.authorize_connection(connection=web_socket)
        signature_model = get_signature_model(route_handler)
        handler_parameter_model = self.handler_parameter_model
        kwargs = handler_parameter_model.to_kwargs(connection=web_socket)
        for dependency in handler_parameter_model.expected_dependencies:
            kwargs[dependency.key] = await self.handler_parameter_model.resolve_dependency(
                dependency=dependency, connection=web_socket, **kwargs
            )
        parsed_kwargs = signature_model.parse_values_from_connection_kwargs(connection=web_socket, **kwargs)
        fn = cast(AsyncAnyCallable, self.route_handler.fn)
        if isinstance(route_handler.owner, Controller):
            await fn(route_handler.owner, **parsed_kwargs)
        else:
            await fn(**parsed_kwargs)


class ASGIRoute(BaseRoute):
    __slots__ = (
        "route_handler",
        # the rest of __slots__ are defined in BaseRoute and should not be duplicated
        # see: https://stackoverflow.com/questions/472000/usage-of-slots
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        path: str,
        route_handler: ASGIRouteHandler,
    ):
        self.route_handler = route_handler
        super().__init__(
            path=path,
            scope_type=ScopeType.ASGI,
            handler_names=[get_name(cast(AnyCallable, route_handler.fn))],
        )

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI app that authorizes the connection and then awaits the handler function
        """

        if self.route_handler.resolve_guards():
            connection = HTTPConnection(scope=scope, receive=receive)
            await self.route_handler.authorize_connection(connection=connection)
        fn = cast(AnyCallable, self.route_handler.fn)
        if isinstance(self.route_handler.owner, Controller):
            await fn(self.route_handler.owner, scope=scope, receive=receive, send=send)
        else:
            await fn(scope=scope, receive=receive, send=send)


class Router:
    __slots__ = (
        "after_request",
        "before_request",
        "dependencies",
        "guards",
        "owner",
        "path",
        "response_class",
        "response_headers",
        "routes",
    )

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
        # connection-lifecycle hook handlers
        before_request: Optional[BeforeRequestHandler] = None,
        after_request: Optional[AfterRequestHandler] = None,
    ):
        self.owner: Optional["Router"] = None
        self.routes: List[BaseRoute] = []
        self.path = normalize_path(path)
        self.response_class = response_class
        self.dependencies = dependencies
        self.response_headers = response_headers
        self.guards = guards
        self.before_request = before_request
        self.after_request = after_request
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
                for route_handler in route.route_handlers:
                    for method in route_handler.http_methods:
                        route_map[route.path][method] = route_handler  # type: ignore
            else:
                route_map[route.path] = cast(WebSocketRoute, route).route_handler
        return route_map

    @staticmethod
    def map_route_handlers(
        value: Union[Controller, BaseRouteHandler, "Router"],
    ) -> ItemsView[str, Union[WebsocketRouteHandler, ASGIRoute, Dict[HttpMethod, HTTPRouteHandler]]]:
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
                        handlers_map[path] = cast(Union[WebsocketRouteHandler, ASGIRouteHandler], route_handler)
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
        value.owner = self
        return cast(Union[Controller, BaseRouteHandler, "Router"], value)

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
                route_handlers = unique(list(cast(Dict[HttpMethod, HTTPRouteHandler], handler_or_method_map).values()))
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
