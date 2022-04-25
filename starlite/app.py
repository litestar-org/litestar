from typing import Any, Dict, List, Optional, Set, Union, cast

from openapi_schema_pydantic import OpenAPI, Schema
from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from pydantic import Extra, validate_arguments
from pydantic.typing import AnyCallable
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response as StarletteResponse
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp, Receive, Scope, Send
from typing_extensions import Type

from starlite.asgi import StarliteASGIRouter
from starlite.config import (
    CacheConfig,
    CORSConfig,
    OpenAPIConfig,
    StaticFilesConfig,
    TemplateConfig,
)
from starlite.connection import Request
from starlite.datastructures import State
from starlite.enums import MediaType
from starlite.exceptions import HTTPException
from starlite.handlers import BaseRouteHandler, HTTPRouteHandler, asgi
from starlite.openapi.path_item import create_path_item
from starlite.plugins.base import PluginProtocol
from starlite.provide import Provide
from starlite.response import Response
from starlite.router import Router
from starlite.routes import ASGIRoute, BaseRoute, HTTPRoute, WebSocketRoute
from starlite.signature import model_function_signature
from starlite.template import TemplateEngineProtocol
from starlite.types import (
    AfterRequestHandler,
    BeforeRequestHandler,
    ControllerRouterHandler,
    ExceptionHandler,
    Guard,
    LifeCycleHandler,
    MiddlewareProtocol,
    ResponseHeader,
)
from starlite.utils import normalize_path

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig(title="Starlite API", version="1.0.0")
DEFAULT_CACHE_CONFIG = CacheConfig()


class Starlite(Router):
    __slots__ = (
        "asgi_router",
        "debug",
        "exception_handlers",
        "middleware_stack",
        "openapi_schema",
        "plugins",
        "state",
        "route_map",
        "static_paths",
        "plain_routes",
        "template_engine",
        "cache_config",
        # the rest of __slots__ are defined in Router and should not be duplicated
        # see: https://stackoverflow.com/questions/472000/usage-of-slots
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        route_handlers: List[ControllerRouterHandler],
        allowed_hosts: Optional[List[str]] = None,
        cors_config: Optional[CORSConfig] = None,
        debug: bool = False,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]] = None,
        on_shutdown: Optional[List[LifeCycleHandler]] = None,
        on_startup: Optional[List[LifeCycleHandler]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
        plugins: Optional[List[PluginProtocol]] = None,
        # connection-lifecycle hook handlers
        before_request: Optional[BeforeRequestHandler] = None,
        after_request: Optional[AfterRequestHandler] = None,
        # static files
        static_files_config: Optional[Union[StaticFilesConfig, List[StaticFilesConfig]]] = None,
        # template
        template_config: Optional[TemplateConfig] = None,
        # cache
        cache_config: CacheConfig = DEFAULT_CACHE_CONFIG,
    ):
        self.debug = debug
        self.state = State()
        self.plugins = plugins or []
        self.routes: List[BaseRoute] = []
        self.route_map: Dict[str, Any] = {}
        self.static_paths = set()
        self.plain_routes: Set[str] = set()
        self.cache_config = cache_config
        super().__init__(
            dependencies=dependencies,
            guards=guards,
            path="",
            response_class=response_class,
            response_headers=response_headers,
            route_handlers=route_handlers,
            before_request=before_request,
            after_request=after_request,
        )
        self.asgi_router = StarliteASGIRouter(on_shutdown=on_shutdown or [], on_startup=on_startup or [], app=self)
        self.exception_handlers: Dict[Union[int, Type[Exception]], ExceptionHandler] = exception_handlers or {}
        self.middleware_stack: ASGIApp = self.build_middleware_stack(
            user_middleware=middleware or [], cors_config=cors_config, allowed_hosts=allowed_hosts
        )
        if openapi_config:
            self.openapi_schema = self.create_openapi_schema_model(openapi_config=openapi_config)
            self.register(openapi_config.openapi_controller)
        else:
            self.openapi_schema = None
        if static_files_config:
            for config in static_files_config if isinstance(static_files_config, list) else [static_files_config]:
                path = normalize_path(config.path)
                self.static_paths.add(path)
                static_files = StaticFiles(html=config.html_mode, check_dir=False)
                static_files.all_directories = config.directories  # type: ignore
                self.register(asgi(path=path)(static_files))
        if template_config:
            self.template_engine: Optional[TemplateEngineProtocol] = template_config.engine(template_config.directory)
        else:
            self.template_engine = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        if scope["type"] == "lifespan":
            await self.asgi_router.lifespan(scope, receive, send)
            return
        try:
            scope["state"] = {}
            await self.middleware_stack(scope, receive, send)
        except Exception as e:  # pylint: disable=broad-except
            await self.handle_exception(scope=scope, receive=receive, send=send, exc=e)

    async def handle_exception(self, scope: Scope, receive: Receive, send: Send, exc: Exception) -> None:
        """
        Determine what exception handler to use given the current scope, and handle an appropriate response
        """
        status_code = exc.status_code if isinstance(exc, StarletteHTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
        if scope["type"] == "http":
            exception_handler = (
                self.exception_handlers.get(status_code)
                or self.exception_handlers.get(exc.__class__)
                or self.default_http_exception_handler
            )
            response = exception_handler(Request(scope=scope, receive=receive, send=send), exc)
            await response(scope=scope, receive=receive, send=send)
        else:
            # The 4000+ code range for websockets is customizable, hence we simply add it to the http status code
            status_code += 4000
            reason = repr(exc)
            await send({"type": "websocket.close", "code": status_code, "reason": reason})

    def construct_route_map(self) -> None:  # noqa: C901
        """
        Create a map of the app's routes. This map is used in the asgi router to route requests.

        """
        if "_components" not in self.route_map:
            self.route_map["_components"] = set()
        for route in self.routes:
            path = route.path
            if route.path_parameters or path in self.static_paths:
                for param_definition in route.path_parameters:
                    path = path.replace(param_definition["full"], "")
                path = path.replace("{}", "*")
                cur = self.route_map
                components = ["/", *[component for component in path.split("/") if component]]
                for component in components:
                    components_set = cast(Set[str], cur["_components"])
                    components_set.add(component)
                    if component not in cur:
                        cur[component] = {"_components": set()}
                    cur = cast(Dict[str, Any], cur[component])
            else:
                self.route_map[path] = {"_components": set()}
                cur = self.route_map[path]
                self.plain_routes.add(path)
            if "_handlers" not in cur:
                cur["_handlers"] = {}
            if "_handler_types" not in cur:
                cur["_handler_types"] = set()
            if path in self.static_paths:
                cur["static_path"] = path
            handler_types = cast(Set[str], cur["_handler_types"])
            handler_types.add(route.scope_type.value)
            handlers = cast(Dict[str, BaseRoute], cur["_handlers"])
            if isinstance(route, HTTPRoute):
                handlers["http"] = route
            elif isinstance(route, WebSocketRoute):
                handlers["websocket"] = route
            else:
                handlers["asgi"] = route

    def register(self, value: ControllerRouterHandler) -> None:  # type: ignore[override]
        """
        Register a Controller, Route instance or RouteHandler on the app.

        Calls Router.register() and then creates a signature model for all handlers.
        """
        routes = super().register(value=value)
        for route in routes:
            if isinstance(route, HTTPRoute):
                route_handlers = route.route_handlers
            else:
                route_handlers = [cast(Union[WebSocketRoute, ASGIRoute], route).route_handler]  # type: ignore
            for route_handler in route_handlers:
                self.create_handler_signature_model(route_handler=route_handler)
                route_handler.resolve_guards()
                if isinstance(route_handler, HTTPRouteHandler):
                    route_handler.resolve_response_class()
                    route_handler.resolve_before_request()
                    route_handler.resolve_after_request()
            if isinstance(route, HTTPRoute):
                route.create_handler_map()
            elif isinstance(route, WebSocketRoute):
                route.handler_parameter_model = route.create_handler_kwargs_model(route.route_handler)
        self.construct_route_map()

    def create_handler_signature_model(self, route_handler: BaseRouteHandler) -> None:
        """
        Creates function signature models for all route handler functions and provider dependencies
        """
        if not route_handler.signature_model:
            route_handler.signature_model = model_function_signature(
                fn=cast(AnyCallable, route_handler.fn), plugins=self.plugins
            )
        for provider in list(route_handler.resolve_dependencies().values()):
            if not provider.signature_model:
                provider.signature_model = model_function_signature(fn=provider.dependency, plugins=self.plugins)

    def build_middleware_stack(
        self,
        user_middleware: List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]],
        allowed_hosts: Optional[List[str]],
        cors_config: Optional[CORSConfig],
    ) -> ASGIApp:
        """
        Builds the middleware stack by passing middlewares in a specific order
        """
        current_app: ASGIApp = self.asgi_router
        # last added middleware will be on the top of stack and it will therefore be called first.
        # we therefore need to reverse the middlewares to keep the call order according to
        # the middlewares' list provided by the user
        for middleware in reversed(user_middleware):
            if isinstance(middleware, Middleware):
                current_app = middleware.cls(app=current_app, **middleware.options)
            else:
                current_app = middleware(app=current_app)
        if allowed_hosts:
            current_app = TrustedHostMiddleware(app=current_app, allowed_hosts=allowed_hosts)
        if cors_config:
            current_app = CORSMiddleware(app=current_app, **cors_config.dict())
        return current_app

    def default_http_exception_handler(self, request: Request, exc: Exception) -> StarletteResponse:
        """Default handler for exceptions subclassed from HTTPException"""
        status_code = exc.status_code if isinstance(exc, StarletteHTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
        if status_code == HTTP_500_INTERNAL_SERVER_ERROR and self.debug:
            # in debug mode, we just use the serve_middleware to create an HTML formatted response for us
            server_middleware = ServerErrorMiddleware(app=self)
            return server_middleware.debug_response(request=request, exc=exc)
        if isinstance(exc, HTTPException):
            content = {"detail": exc.detail, "extra": exc.extra}
        elif isinstance(exc, StarletteHTTPException):
            content = {"detail": exc.detail}
        else:
            content = {"detail": repr(exc)}
        return Response(
            media_type=MediaType.JSON,
            content=content,
            status_code=status_code,
        )

    def create_openapi_schema_model(self, openapi_config: OpenAPIConfig) -> OpenAPI:
        """
        Updates the OpenAPI schema with all paths registered on the root router
        """
        openapi_schema = openapi_config.to_openapi_schema()
        openapi_schema.paths = {}
        for route in self.routes:
            if (
                isinstance(route, HTTPRoute)
                and any(route_handler.include_in_schema for route_handler, _ in route.route_handler_map.values())
                and (route.path_format or "/") not in openapi_schema.paths
            ):
                openapi_schema.paths[route.path_format or "/"] = create_path_item(
                    route=route, create_examples=openapi_config.create_examples
                )
        # we have to monkey patch the "openapi-schema-pydantic" library, because it doesn't allow extra which causes
        # failures with third party libs such as ormar.
        Schema.Config.extra = Extra.ignore
        return construct_open_api_with_schema_class(openapi_schema)
