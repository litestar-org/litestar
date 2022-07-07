from typing import Any, Dict, List, Optional, Set, Union, cast

from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from openapi_schema_pydantic.v3.v3_1_0.open_api import OpenAPI
from pydantic import validate_arguments
from pydantic.typing import AnyCallable
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send
from typing_extensions import Type

from starlite.asgi import StarliteASGIRouter
from starlite.config import (
    CacheConfig,
    CORSConfig,
    GZIPConfig,
    OpenAPIConfig,
    StaticFilesConfig,
    TemplateConfig,
)
from starlite.datastructures import State
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.asgi import ASGIRouteHandler, asgi
from starlite.handlers.base import BaseRouteHandler
from starlite.handlers.http import HTTPRouteHandler
from starlite.handlers.websocket import WebsocketRouteHandler
from starlite.middleware import ExceptionHandlerMiddleware
from starlite.openapi.path_item import create_path_item
from starlite.plugins.base import PluginProtocol
from starlite.provide import Provide
from starlite.response import Response
from starlite.router import Router
from starlite.routes import ASGIRoute, BaseRoute, HTTPRoute, WebSocketRoute
from starlite.signature import SignatureModelFactory
from starlite.types import (
    AfterRequestHandler,
    BeforeRequestHandler,
    ControllerRouterHandler,
    ExceptionHandler,
    Guard,
    LifeCycleHandler,
    Middleware,
    ResponseHeader,
)
from starlite.utils import normalize_path
from starlite.utils.templates import create_template_engine

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig(title="Starlite API", version="1.0.0")
DEFAULT_CACHE_CONFIG = CacheConfig()


class Starlite(Router):
    __slots__ = (
        "allowed_hosts",
        "asgi_handler",
        "asgi_router",
        "cache_config",
        "cors_config",
        "debug",
        "gzip_config",
        "openapi_schema",
        "plain_routes",
        "plugins",
        "route_map",
        "state",
        "static_paths",
        "template_engine",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        allowed_hosts: Optional[List[str]] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        cache_config: CacheConfig = DEFAULT_CACHE_CONFIG,
        cors_config: Optional[CORSConfig] = None,
        debug: bool = False,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        gzip_config: Optional[GZIPConfig] = None,
        middleware: Optional[List[Middleware]] = None,
        on_shutdown: Optional[List[LifeCycleHandler]] = None,
        on_startup: Optional[List[LifeCycleHandler]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG,
        plugins: Optional[List[PluginProtocol]] = None,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
        route_handlers: List[ControllerRouterHandler],
        static_files_config: Optional[Union[StaticFilesConfig, List[StaticFilesConfig]]] = None,
        template_config: Optional[TemplateConfig] = None,
    ):
        self.allowed_hosts = allowed_hosts
        self.cache_config = cache_config
        self.cors_config = cors_config
        self.debug = debug
        self.gzip_config = gzip_config
        self.plain_routes: Set[str] = set()
        self.plugins = plugins or []
        self.route_map: Dict[str, Any] = {}
        self.routes: List[BaseRoute] = []
        self.state = State()
        self.static_paths = set()

        super().__init__(
            dependencies=dependencies,
            guards=guards,
            path="",
            response_class=response_class,
            response_headers=response_headers,
            route_handlers=route_handlers,
            before_request=before_request,
            after_request=after_request,
            middleware=middleware,
            exception_handlers=exception_handlers,
        )

        self.asgi_router = StarliteASGIRouter(on_shutdown=on_shutdown or [], on_startup=on_startup or [], app=self)
        self.asgi_handler = self.create_asgi_handler()
        self.openapi_schema: Optional[OpenAPI] = None
        if openapi_config:
            self.openapi_schema = self.create_openapi_schema_model(openapi_config=openapi_config)
            self.register(openapi_config.openapi_controller)
        if static_files_config:
            for config in static_files_config if isinstance(static_files_config, list) else [static_files_config]:
                path = normalize_path(config.path)
                self.static_paths.add(path)
                static_files = StaticFiles(html=config.html_mode, check_dir=False)
                static_files.all_directories = config.directories  # type: ignore
                self.register(asgi(path=path)(static_files))
        self.template_engine = create_template_engine(template_config)

    def create_asgi_handler(self) -> ASGIApp:
        """
        Creates an ASGIApp that wraps the ASGI router inside an exception handler.

        If CORS or TruseedHost configs are provided to the constructor, they will wrap the router as well.
        """
        asgi_handler: ASGIApp = self.asgi_router
        if self.gzip_config:
            asgi_handler = GZipMiddleware(app=asgi_handler, **self.gzip_config.dict())
        if self.allowed_hosts:
            asgi_handler = TrustedHostMiddleware(app=asgi_handler, allowed_hosts=self.allowed_hosts)
        if self.cors_config:
            asgi_handler = CORSMiddleware(app=asgi_handler, **self.cors_config.dict())
        return self.wrap_in_exception_handler(asgi_handler, exception_handlers=self.exception_handlers or {})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The application entry point.
        Lifespan events (startup / shutdown) are sent to the lifespan handler, otherwise the ASGI handler is used
        """
        scope["app"] = self
        if scope["type"] == "lifespan":
            await self.asgi_router.lifespan(scope, receive, send)
            return
        scope["state"] = {}
        await self.asgi_handler(scope, receive, send)

    def wrap_in_exception_handler(
        self, app: ASGIApp, exception_handlers: Dict[Union[int, Type[Exception]], ExceptionHandler]
    ) -> ASGIApp:
        """
        Wraps the given ASGIApp in an instance of ExceptionHandlerMiddleware
        """

        return ExceptionHandlerMiddleware(app=app, exception_handlers=exception_handlers, debug=self.debug)

    def construct_route_map(self) -> None:  # noqa: C901 # pylint: disable=R0912
        """
        Create a map of the app's routes. This map is used in the asgi router to route requests.

        """
        seen_param_paths = set()
        if "_components" not in self.route_map:
            self.route_map["_components"] = set()
        for route in self.routes:
            path = route.path
            if route.path_parameters or path in self.static_paths:
                for param_definition in route.path_parameters:
                    path = path.replace(param_definition["full"], "")
                path = path.replace("{}", "*")
                if path in seen_param_paths:
                    raise ImproperlyConfiguredException("Should not use routes with conflicting path parameters")
                seen_param_paths.add(path)
                cur = self.route_map
                components = ["/", *[component for component in path.split("/") if component]]
                for component in components:
                    components_set = cast(Set[str], cur["_components"])
                    components_set.add(component)
                    if component not in cur:
                        cur[component] = {"_components": set()}
                    cur = cast(Dict[str, Any], cur[component])
            else:
                if path not in self.route_map:
                    self.route_map[path] = {"_components": set()}
                self.plain_routes.add(path)
                cur = self.route_map[path]
            if "_path_parameters" not in cur:
                cur["_path_parameters"] = route.path_parameters
            if "_asgi_handlers" not in cur:
                cur["_asgi_handlers"] = {}
            if "_is_asgi" not in cur:
                cur["_is_asgi"] = False
            if path in self.static_paths:
                cur["static_path"] = path
                cur["_is_asgi"] = True
            asgi_handlers = cast(Dict[str, ASGIApp], cur["_asgi_handlers"])
            if isinstance(route, HTTPRoute):
                for method, handler_mapping in route.route_handler_map.items():
                    handler, _ = handler_mapping
                    asgi_handlers[method] = self.build_route_middleware_stack(route, handler)
            elif isinstance(route, WebSocketRoute):
                asgi_handlers["websocket"] = self.build_route_middleware_stack(route, route.route_handler)
            elif isinstance(route, ASGIRoute):
                asgi_handlers["asgi"] = self.build_route_middleware_stack(route, route.route_handler)
                cur["_is_asgi"] = True

    def build_route_middleware_stack(
        self,
        route: Union[HTTPRoute, WebSocketRoute, ASGIRoute],
        route_handler: Union[HTTPRouteHandler, WebsocketRouteHandler, ASGIRouteHandler],
    ) -> ASGIApp:
        """Constructs a middleware stack that serves as the point of entry for each route"""

        # we wrap the route.handle method in the ExceptionHandlerMiddleware
        asgi_handler = self.wrap_in_exception_handler(
            app=route.handle, exception_handlers=route_handler.resolve_exception_handlers()
        )

        for middleware in route_handler.resolve_middleware():
            if isinstance(middleware, StarletteMiddleware):
                asgi_handler = middleware.cls(app=asgi_handler, **middleware.options)
            else:
                asgi_handler = middleware(app=asgi_handler)

        # we wrap the entire stack again in ExceptionHandlerMiddleware
        return self.wrap_in_exception_handler(
            app=asgi_handler, exception_handlers=route_handler.resolve_exception_handlers()
        )

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
                route_handler.resolve_middleware()
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
            route_handler.signature_model = SignatureModelFactory(
                fn=cast(AnyCallable, route_handler.fn),
                plugins=self.plugins,
                provided_dependency_names=route_handler.dependency_name_set,
            ).model()
        for provider in list(route_handler.resolve_dependencies().values()):
            if not provider.signature_model:
                provider.signature_model = SignatureModelFactory(
                    fn=provider.dependency,
                    plugins=self.plugins,
                    provided_dependency_names=route_handler.dependency_name_set,
                ).model()

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
        return cast(OpenAPI, construct_open_api_with_schema_class(openapi_schema))
