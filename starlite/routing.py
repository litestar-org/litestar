import re
from abc import ABC
from inspect import isclass
from itertools import chain
from typing import Any, Dict, ItemsView, List, Optional, Set, Tuple, Union, cast
from uuid import UUID

from pydantic import validate_arguments
from pydantic.fields import Undefined
from pydantic.typing import AnyCallable
from starlette.routing import get_name
from starlette.types import Receive, Scope, Send
from typing_extensions import Type

from starlite.controller import Controller
from starlite.enums import HttpMethod, ScopeType
from starlite.exceptions import ImproperlyConfiguredException, MethodNotAllowedException
from starlite.handlers import (
    ASGIRouteHandler,
    BaseRouteHandler,
    HTTPRouteHandler,
    WebsocketRouteHandler,
)
from starlite.provide import Provide
from starlite.request import Request, WebSocket
from starlite.response import Response
from starlite.signature import SignatureModel
from starlite.types import (
    AfterRequestHandler,
    BeforeRequestHandler,
    ControllerRouterHandler,
    Guard,
    Method,
    ResponseHeader,
)
from starlite.utils import find_index, join_paths, normalize_path, unique

param_match_regex = re.compile(r"{(.*?)}")


class HandlerKwargsModel:
    __slots__ = (
        "expected_data",
        "expected_cookie_params",
        "expected_dependencies",
        "expected_header_params",
        "expected_path_params",
        "expected_query_params",
    )

    def __init__(
        self,
        *,
        expected_data: bool,
        expected_cookie_params: Set[Tuple[str, bool]],
        expected_dependencies: Set[Tuple[str, bool]],
        expected_header_params: Set[Tuple[str, bool]],
        expected_path_params: Set[Tuple[str, bool]],
        expected_query_params: Set[Tuple[str, bool]],
    ) -> None:
        self.expected_data = expected_data
        self.expected_dependencies = expected_dependencies
        self.expected_cookie_params = expected_cookie_params
        self.expected_header_params = expected_header_params
        self.expected_path_params = expected_path_params
        self.expected_query_params = expected_query_params


def get_expected_dependencies(
    signature_model: Type[SignatureModel], dependencies: Dict[str, Provide]
) -> Set[Tuple[str, bool]]:
    expected_dependencies: Set[Tuple[str, bool]] = set()
    for key, value in dependencies.items():
        model_field = signature_model.__fields__.get(key)
        if model_field:
            expected_dependencies.add((key, model_field.default is not Undefined or model_field.allow_none))
            expected_dependencies.update(
                get_expected_dependencies(signature_model=value.signature_model, dependencies=dependencies)
            )
    return expected_dependencies


class BaseRoute(ABC):
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
                raise ImproperlyConfiguredException("path parameter must declare a type: '{parameter_name:type}'")
            param_name, param_type = (p.strip() for p in param.split(":"))
            path_format = path_format.replace(param, param_name)
            path_parameters.append({"name": param_name, "type": param_type_map[param_type], "full": param})
        return path, path_format, path_parameters

    def create_handler_kwargs_model(self, route_handler: BaseRouteHandler) -> HandlerKwargsModel:
        """
        This function pre-determines what parameters are required for a given combination of route + route handler.

        This function during the application bootstrap process, to ensure optimal runtime performance.
        """
        signature_model = route_handler.signature_model
        dependencies = route_handler.resolve_dependencies()
        route_path_parameters = {p["name"] for p in self.path_parameters}
        expected_dependencies = get_expected_dependencies(signature_model=signature_model, dependencies=dependencies)

        for dependency_name in expected_dependencies:
            if dependency_name in route_path_parameters:
                raise ImproperlyConfiguredException(
                    f"path parameter and dependency kwarg have a similar key - {dependency_name}"
                )

        expected_path_parameters: Set[Tuple[str, bool]] = set()

        for key in route_path_parameters:
            model_field = signature_model.__fields__.get(key)
            if model_field:
                expected_path_parameters.add((key, model_field.default is not Undefined or model_field.allow_none))

        expected_header_parameters: Set[Tuple[str, bool]] = set()
        expected_cookie_parameters: Set[Tuple[str, bool]] = set()
        expected_query_parameters: Set[Tuple[str, bool]] = set()

        for field_name, model_field in signature_model.__fields__.items():
            model_info = model_field.field_info
            extra_keys = set(model_info.extra)
            has_default = model_field.default is not Undefined
            is_required = model_info.extra.get("required")
            if "query" in extra_keys and model_info.extra["query"]:
                expected_query_parameters.add((field_name, is_required and not has_default))
            elif "header" in extra_keys and model_info.extra["header"]:
                expected_header_parameters.add((field_name, is_required and not has_default))
            elif "cookie" in extra_keys and model_info.extra["cookie"]:
                expected_cookie_parameters.add((field_name, is_required and not has_default))

        for key in set(signature_model.__fields__) - {
            *expected_query_parameters,
            *expected_cookie_parameters,
            *expected_header_parameters,
            *expected_dependencies,
            *expected_path_parameters,
            "data",
        }:
            model_field = signature_model.__fields__[key]
            expected_query_parameters.add((key, model_field.default is not Undefined or model_field.allow_none))

        expected_data = False

        data_model_field = signature_model.__fields__.get("data")
        if data_model_field:
            expected_data = data_model_field.default is Undefined and not data_model_field.allow_none
        return HandlerKwargsModel(
            expected_data=expected_data,
            expected_dependencies=expected_dependencies,
            expected_path_params=expected_path_parameters,
            expected_query_params=expected_query_parameters,
            expected_cookie_params=expected_cookie_parameters,
            expected_header_params=expected_header_parameters,
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
        self.route_handler_map: Dict[Method, Tuple[HTTPRouteHandler, HandlerKwargsModel]] = {}
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
        handler, parameter_model = self.route_handler_map[request.method]
        response = await handler.handle_request(request=request)
        await response(scope, receive, send)

    def create_handler_map(self):
        """
        Parses the passed in route_handlers and returns a mapping of http-methods and route handlers
        """
        for route_handler in self.route_handlers:
            kwargs_model = self.create_handler_kwargs_model(route_handler=route_handler)
            for http_method in route_handler.http_methods:
                if self.route_handler_map.get(http_method):
                    raise ImproperlyConfiguredException(
                        f"handler already registered for path {self.path!r} and http method {http_method}"
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
        self.handler_parameter_model: Optional[HandlerKwargsModel] = None
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
        web_socket: WebSocket[Any, Any] = WebSocket(scope=scope, receive=receive, send=send)
        await self.route_handler.handle_websocket(web_socket=web_socket)


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
        ASGI app that creates a WebSocket from the passed in args, and then awaits the handler function
        """
        await self.route_handler.handle_asgi(scope=scope, receive=receive, send=send)


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
                route = WebSocketRoute(path=path, route_handler=handler_or_method_map)
                self.routes.append(route)
            elif isinstance(handler_or_method_map, ASGIRouteHandler):
                route = ASGIRoute(path=path, route_handler=handler_or_method_map)
                self.routes.append(route)
            else:
                existing_handlers: List[HTTPRouteHandler] = list(self.route_handler_method_map.get(path, {}).values())
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
