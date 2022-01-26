import re
from abc import ABC
from inspect import isawaitable, isclass
from itertools import chain
from typing import (
    Any,
    Dict,
    ItemsView,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)
from uuid import UUID

from pydantic import validate_arguments
from pydantic.fields import ModelField, Undefined
from pydantic.typing import AnyCallable
from starlette.requests import HTTPConnection
from starlette.routing import get_name
from starlette.types import Receive, Scope, Send
from typing_extensions import Type

from starlite.constants import RESERVED_FIELD_NAMES
from starlite.controller import Controller
from starlite.enums import HttpMethod, RequestEncodingType, ScopeType
from starlite.exceptions import (
    ImproperlyConfiguredException,
    MethodNotAllowedException,
    ValidationException,
)
from starlite.handlers import (
    ASGIRouteHandler,
    BaseRouteHandler,
    HTTPRouteHandler,
    WebsocketRouteHandler,
)
from starlite.provide import Provide
from starlite.request import Request, WebSocket, handle_multipart
from starlite.response import Response
from starlite.signature import SignatureModel
from starlite.types import (
    AfterRequestHandler,
    AsyncAnyCallable,
    BeforeRequestHandler,
    ControllerRouterHandler,
    Guard,
    Method,
    ReservedKwargs,
    ResponseHeader,
)
from starlite.utils import find_index, join_paths, normalize_path, unique

param_match_regex = re.compile(r"{(.*?)}")


class ParameterDefinition(NamedTuple):
    field_name: str
    field_alias: str
    is_required: bool
    default_value: Any


def merge_parameter_sets(first: Set[ParameterDefinition], second: Set[ParameterDefinition]):
    """
    Given two sets of parameter definitions, coming from different dependencies for example, merge them into a single set
    """
    result: Set[ParameterDefinition] = first.intersection(second)
    difference = first.symmetric_difference(second)
    for param in difference:
        if param.is_required:
            result.add(param)
        elif any(p != param and p.field_alias == param.field_alias and p.is_required for p in difference):
            continue
        else:
            result.add(param)
    return result


class KwargsModel:
    __slots__ = (
        "expected_cookie_params",
        "expected_dependencies",
        "expected_form_data",
        "expected_header_params",
        "expected_path_params",
        "expected_query_params",
        "expected_reserved_kwargs",
    )

    def __init__(
        self,
        *,
        expected_dependencies: Set[Tuple[str, bool]],
        expected_form_data: Optional[Tuple[RequestEncodingType, ModelField]],
        expected_cookie_params: Set[ParameterDefinition],
        expected_header_params: Set[ParameterDefinition],
        expected_path_params: Set[ParameterDefinition],
        expected_query_params: Set[ParameterDefinition],
        expected_reserved_kwargs: Set[ReservedKwargs],
    ) -> None:
        self.expected_dependencies = expected_dependencies
        self.expected_form_data = expected_form_data
        self.expected_cookie_params = expected_cookie_params
        self.expected_header_params = expected_header_params
        self.expected_path_params = expected_path_params
        self.expected_query_params = expected_query_params
        self.expected_reserved_kwargs = expected_reserved_kwargs

    @classmethod
    def create_for_signature_model(
        cls, signature_model: SignatureModel, dependencies: Dict[str, Provide], path_parameters: Set[str]
    ) -> "KwargsModel":
        """
        This function pre-determines what parameters are required for a given combination of route + route handler.

        This function during the application bootstrap process, to ensure optimal runtime performance.
        """
        expected_reserved_kwargs = {
            field_name for field_name in signature_model.__fields__ if field_name in RESERVED_FIELD_NAMES
        }
        expected_dependencies: Set[Tuple[str, bool]] = set()
        expected_path_parameters: Set[ParameterDefinition] = set()
        expected_header_parameters: Set[ParameterDefinition] = set()
        expected_cookie_parameters: Set[ParameterDefinition] = set()
        expected_query_parameters: Set[ParameterDefinition] = set()

        for key, value in dependencies.items():
            model_field = signature_model.__fields__.get(key)
            if model_field:
                expected_dependencies.add((key, model_field.default is not Undefined or model_field.allow_none))

        for dependency_name in expected_dependencies:
            if dependency_name in path_parameters:
                raise ImproperlyConfiguredException(
                    f"path parameter and dependency kwarg have a similar key - {dependency_name}"
                )
        for key in path_parameters:
            model_field = signature_model.__fields__.get(key)
            if model_field:
                default = model_field.default if model_field.default is not Undefined else None
                if model_field:
                    expected_path_parameters.add(
                        ParameterDefinition(
                            field_name=key,
                            field_alias=key,
                            default_value=default,
                            is_required=default is None and not model_field.allow_none and default is None,
                        )
                    )
        aliased_fields = set()
        for field_name, model_field in signature_model.__fields__.items():
            model_info = model_field.field_info
            extra_keys = set(model_info.extra)
            default = model_field.default if model_field.default is not Undefined else None
            is_required = model_info.extra.get("required")
            if "query" in extra_keys and model_info.extra["query"]:
                aliased_fields.add(field_name)
                field_alias = model_info.extra["query"]
                expected_query_parameters.add(
                    ParameterDefinition(
                        field_name=field_name,
                        field_alias=field_alias,
                        default_value=default,
                        is_required=is_required and default is None,
                    )
                )
            elif "header" in extra_keys and model_info.extra["header"]:
                aliased_fields.add(field_name)
                field_alias = model_info.extra["header"]
                expected_header_parameters.add(
                    ParameterDefinition(
                        field_name=field_name,
                        field_alias=field_alias,
                        default_value=default,
                        is_required=is_required and default is None,
                    )
                )
            elif "cookie" in extra_keys and model_info.extra["cookie"]:
                aliased_fields.add(field_name)
                field_alias = model_info.extra["cookie"]
                expected_cookie_parameters.add(
                    ParameterDefinition(
                        field_name=field_name,
                        field_alias=field_alias,
                        default_value=default,
                        is_required=is_required and default is None,
                    )
                )

        for key in set(signature_model.__fields__) - {
            *{dependency_name for dependency_name, _ in expected_dependencies},
            *{param.field_name for param in expected_path_parameters},
            *expected_reserved_kwargs,
            *aliased_fields,
            "data",
        }:
            model_field = signature_model.__fields__[key]
            default = model_field.default if model_field.default is not Undefined else None
            expected_query_parameters.add(
                ParameterDefinition(
                    field_name=key,
                    field_alias=key,
                    default_value=default,
                    is_required=default is None and not model_field.allow_none and default is None,
                )
            )

        expected_form_data = None
        data_model_field = signature_model.__fields__.get("data")
        if data_model_field:
            media_type = data_model_field.field_info.extra.get("media_type")
            if media_type in [
                RequestEncodingType.MULTI_PART,
                RequestEncodingType.URL_ENCODED,
            ]:
                expected_form_data = (media_type, data_model_field)
        for dependency_name, _ in expected_dependencies:
            provider = dependencies[dependency_name]
            kwarg_model = cls.create_for_signature_model(
                signature_model=cast(SignatureModel, provider.signature_model),
                dependencies=dependencies,
                path_parameters=path_parameters,
            )
            expected_path_parameters = merge_parameter_sets(expected_path_parameters, kwarg_model.expected_path_params)
            expected_query_parameters = merge_parameter_sets(
                expected_query_parameters, kwarg_model.expected_query_params
            )
            expected_cookie_parameters = merge_parameter_sets(
                expected_cookie_parameters, kwarg_model.expected_cookie_params
            )
            expected_header_parameters = merge_parameter_sets(
                expected_header_parameters, kwarg_model.expected_header_params
            )

            if "data" in expected_reserved_kwargs and "data" in kwarg_model.expected_reserved_kwargs:
                if (expected_form_data and not kwarg_model.expected_form_data) or (
                    not expected_form_data and kwarg_model.expected_form_data
                ):
                    raise ImproperlyConfiguredException(
                        "Dependencies have incompatible 'data' kwarg types- one expects JSON and the other expects form data"
                    )
                if expected_form_data and kwarg_model.expected_form_data:
                    local_media_type, _ = expected_form_data
                    dependency_media_type, _ = kwarg_model.expected_form_data
                    if local_media_type != dependency_media_type:
                        raise ImproperlyConfiguredException(
                            "Dependencies have incompatible form data encoding - one expects url-encoded and the other expects multi-part"
                        )
            expected_reserved_kwargs.update()
        return KwargsModel(
            expected_form_data=expected_form_data,
            expected_dependencies=expected_dependencies,
            expected_path_params=expected_path_parameters,
            expected_query_params=expected_query_parameters,
            expected_cookie_params=expected_cookie_parameters,
            expected_header_params=expected_header_parameters,
            expected_reserved_kwargs=expected_reserved_kwargs,
        )

    def to_kwargs(self, connection: Union[WebSocket, Request]) -> Dict[str, Any]:
        """
        Return a dictionary of kwargs. Async values, i.e. CoRoutines, are not resolved to ensure this function is sync.
        """
        reserved_kwargs: Dict[str, Any] = {}
        if self.expected_reserved_kwargs:
            if "state" in self.expected_reserved_kwargs:
                reserved_kwargs["state"] = connection.app.state.copy()
            elif "headers" in self.expected_reserved_kwargs:
                reserved_kwargs["headers"] = dict(connection.headers)
            elif "cookies" in self.expected_reserved_kwargs:
                reserved_kwargs["cookies"] = connection.cookies
            elif "query" in self.expected_reserved_kwargs:
                reserved_kwargs["query"] = connection.query_params
            elif "request" in self.expected_reserved_kwargs:
                reserved_kwargs["request"] = connection
            elif "socket" in self.expected_reserved_kwargs:
                reserved_kwargs["socket"] = connection
            elif "data" in self.expected_reserved_kwargs:
                reserved_kwargs["data"] = self.get_request_data(request=cast(Request, connection))
        try:
            path_params = {
                field_name: connection.path_params[field_alias]
                if is_required
                else connection.path_params.get(field_alias, default)
                for field_name, field_alias, is_required, default in self.expected_path_params
            }
            query_params = {
                field_name: connection.query_params[field_alias]
                if is_required
                else connection.query_params.get(field_alias, default)
                for field_name, field_alias, is_required, default in self.expected_query_params
            }
            header_params = {
                field_name: connection.headers[field_alias]
                if is_required
                else connection.headers.get(field_alias, default)
                for field_name, field_alias, is_required, default in self.expected_header_params
            }
            cookie_params = {
                field_name: connection.cookies[field_alias]
                if is_required
                else connection.cookies.get(field_alias, default)
                for field_name, field_alias, is_required, default in self.expected_cookie_params
            }
            return {**reserved_kwargs, **path_params, **query_params, **header_params, **cookie_params}
        except KeyError as e:
            raise ValidationException(f"Missing required parameter {e.args[0]} for url {connection.url}") from e

    async def get_request_data(self, request: Request) -> Any:
        if self.expected_form_data:
            media_type, model_field = self.expected_form_data
            form_data = await request.form()
            return handle_multipart(media_type=media_type, form_data=form_data, field=model_field)
        return await request.json()


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

    def create_handler_kwargs_model(self, route_handler: BaseRouteHandler) -> KwargsModel:
        """
        Method to create a KwargsModel for a given route handler
        """
        dependencies = route_handler.resolve_dependencies()
        signature_model = cast(SignatureModel, route_handler.signature_model)
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

        handler, parameter_model = self.route_handler_map[request.method]
        if handler.resolved_guards:
            await handler.authorize_connection(connection=request)
        response_data = None
        before_request_handler = handler.resolve_before_request()
        if before_request_handler:
            # run the before_request hook handler
            if before_request_handler:
                response_data = before_request_handler(request)
                if isawaitable(response_data):
                    response_data = await response_data
        if not response_data:
            signature_model = handler.signature_model
            if signature_model.has_kwargs:
                kwargs = parameter_model.to_kwargs(connection=request)
                request_data = kwargs.get("data")
                if request_data:
                    kwargs["data"] = await request_data
                parsed_kwargs = handler.signature_model.parse_values_from_connection_kwargs(
                    connection=request, **kwargs
                )
            else:
                parsed_kwargs = {}
            fn = cast(AnyCallable, handler.fn)
            if signature_model.is_async:
                response_data = await fn(**parsed_kwargs)
            else:
                response_data = handler.fn(**parsed_kwargs)
        response = await handler.to_response(plugins=request.app.plugins, data=response_data)
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
        if route_handler.resolved_guards:
            await route_handler.authorize_connection(connection=web_socket)
        signature_model = route_handler.signature_model
        if signature_model.has_kwargs:
            kwargs = self.handler_parameter_model.to_kwargs(connection=web_socket)
            parsed_kwargs = route_handler.signature_model.parse_values_from_connection_kwargs(
                connection=web_socket, **kwargs
            )
        else:
            parsed_kwargs = {}
        fn = cast(AsyncAnyCallable, self.route_handler.fn)
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
        ASGI app that creates a WebSocket from the passed in args, and then awaits the handler function
        """

        if self.route_handler.resolved_guards:
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
