import pickle
import re
from functools import partial
from inspect import iscoroutinefunction
from itertools import chain
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from uuid import UUID

from anyio.to_thread import run_sync
from pydantic import validate_arguments
from pydantic.typing import AnyCallable
from starlette.requests import HTTPConnection
from starlette.responses import Response as StarletteResponse
from starlette.routing import get_name
from starlette.types import Receive, Scope, Send

from starlite.connection import Request, WebSocket
from starlite.controller import Controller
from starlite.enums import ScopeType
from starlite.exceptions import ImproperlyConfiguredException, MethodNotAllowedException
from starlite.handlers import (
    ASGIRouteHandler,
    BaseRouteHandler,
    HTTPRouteHandler,
    WebsocketRouteHandler,
)
from starlite.kwargs import KwargsModel
from starlite.response import Response
from starlite.signature import get_signature_model
from starlite.types import AsyncAnyCallable, CacheKeyBuilder, Method
from starlite.utils import normalize_path

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

        caching_enabled = route_handler.cache
        response: Optional[Union[Response, StarletteResponse]] = None
        if caching_enabled:
            response = await self.get_cached_response(request=request, route_handler=route_handler)
        if not response:
            response_data = None
            before_request_handler = route_handler.resolve_before_request()
            # run the before_request hook handler
            if before_request_handler:
                if iscoroutinefunction(before_request_handler):
                    response_data = await before_request_handler(request)
                else:
                    response_data = await run_sync(before_request_handler, request)
            if not response_data:
                response_data = await self.get_response_data(
                    route_handler=route_handler, parameter_model=parameter_model, request=request
                )
            response = await route_handler.to_response(
                app=scope["app"],
                data=response_data,
                plugins=request.app.plugins,
            )
            # we cache the response instance
            if caching_enabled:
                await self.set_cached_response(
                    response=response,
                    request=request,
                    route_handler=route_handler,
                )
        await response(scope, receive, send)

    @staticmethod
    async def get_response_data(route_handler: HTTPRouteHandler, parameter_model: KwargsModel, request: Request) -> Any:
        """
        Determines what kwargs are required for the given route handler's 'fn' and calls it
        """
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
        if isinstance(route_handler.owner, Controller):
            fn = partial(cast(AnyCallable, route_handler.fn), route_handler.owner, **parsed_kwargs)
        else:
            fn = partial(cast(AnyCallable, route_handler.fn), **parsed_kwargs)
        if iscoroutinefunction(fn):
            return await fn()
        if route_handler.sync_to_thread:
            return await run_sync(fn)
        return fn()

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

    @staticmethod
    async def get_cached_response(request: Request, route_handler: HTTPRouteHandler) -> Optional[StarletteResponse]:
        """
        Retrieves and un-pickles the cached value, if it exists
        """
        cache_config = request.app.cache_config
        key_builder = cast(CacheKeyBuilder, route_handler.cache_key_builder or cache_config.cache_key_builder)  # type: ignore[misc]
        cache_key = key_builder(request)
        if iscoroutinefunction(cache_config.backend.get):
            cached_value = await cache_config.backend.get(cache_key)
        else:
            cached_value = cache_config.backend.get(cache_key)
        if cached_value:
            return cast(StarletteResponse, pickle.loads(cached_value))  # nosec
        return None

    @staticmethod
    async def set_cached_response(
        response: Union[Response, StarletteResponse], request: Request, route_handler: HTTPRouteHandler
    ) -> None:
        """
        Pickles and caches a response object
        """
        cache_config = request.app.cache_config
        key_builder = cast(CacheKeyBuilder, route_handler.cache_key_builder or cache_config.cache_key_builder)  # type: ignore[misc]
        cache_key = key_builder(request)
        expiration = route_handler.cache if not isinstance(route_handler.cache, bool) else cache_config.expiration
        pickled_response = pickle.dumps(response, pickle.HIGHEST_PROTOCOL)
        if iscoroutinefunction(cache_config.backend.set):
            await cache_config.backend.set(cache_key, pickled_response, expiration)
        else:
            cache_config.backend.set(cache_key, pickled_response, expiration)


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
