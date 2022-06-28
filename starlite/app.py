from typing import Any, Dict, List, Optional, Set, Union, cast

from openapi_schema_pydantic import OpenAPI, Schema
from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from pydantic import Extra, validate_arguments
from pydantic.typing import AnyCallable
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles
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
from starlite.datastructures import State
from starlite.handlers import BaseRouteHandler, HTTPRouteHandler, asgi
from starlite.middleware import ExceptionMiddleware
from starlite.openapi.path_item import create_path_item
from starlite.plugins.base import PluginProtocol
from starlite.provide import Provide
from starlite.response import Response
from starlite.router import Router
from starlite.routes import ASGIRoute, BaseRoute, HTTPRoute, WebSocketRoute
from starlite.signature import model_function_signature
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
        "asgi_router",
        "debug",
        "openapi_schema",
        "plugins",
        "state",
        "route_map",
        "static_paths",
        "plain_routes",
        "template_engine",
        "cache_config",
        "cors_config",
        "allowed_hosts",
        # the rest of __slots__ are defined in Router and should not be duplicated
        # see: https://stackoverflow.com/questions/472000/usage-of-slots
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
        self.debug = debug
        self.state = State()
        self.plugins = plugins or []
        self.routes: List[BaseRoute] = []
        self.route_map: Dict[str, Any] = {}
        self.static_paths = set()
        self.plain_routes: Set[str] = set()
        self.cache_config = cache_config
        self.cors_config = cors_config
        self.allowed_hosts = allowed_hosts

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
        )

        self.asgi_router = StarliteASGIRouter(on_shutdown=on_shutdown or [], on_startup=on_startup or [], app=self)
        self.exception_handlers: Dict[Union[int, Type[Exception]], ExceptionHandler] = exception_handlers or {}
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
        self.template_engine = create_template_engine(template_config)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        if scope["type"] == "lifespan":
            await self.asgi_router.lifespan(scope, receive, send)
            return
        scope["state"] = {}
        await self.asgi_router(scope, receive, send)

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
        self, route: Union[HTTPRoute, WebSocketRoute, ASGIRoute], route_handler: BaseRouteHandler
    ) -> ASGIApp:
        """Constructs a middleware stack that serves as the point of entry for each route"""
        if isinstance(route_handler, HTTPRouteHandler):
            exception_handlers = route_handler.resolve_exception_handlers()
        else:
            exception_handlers = {}
        asgi_handler: ASGIApp = route.handle
        for middleware in route_handler.resolve_middleware():
            if isinstance(middleware, StarletteMiddleware):
                asgi_handler = middleware.cls(app=asgi_handler, **middleware.options)
            else:
                asgi_handler = middleware(app=asgi_handler)
        if self.allowed_hosts:
            asgi_handler = TrustedHostMiddleware(app=asgi_handler, allowed_hosts=self.allowed_hosts)
        if self.cors_config:
            asgi_handler = CORSMiddleware(app=asgi_handler, **self.cors_config.dict())
        return ExceptionMiddleware(app=asgi_handler, exception_handlers=exception_handlers, debug=self.debug)

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
            route_handler.signature_model = model_function_signature(
                fn=cast(AnyCallable, route_handler.fn),
                plugins=self.plugins,
                provided_dependency_names=route_handler.dependency_name_set,
            )
        for provider in list(route_handler.resolve_dependencies().values()):
            if not provider.signature_model:
                provider.signature_model = model_function_signature(
                    fn=provider.dependency,
                    plugins=self.plugins,
                    provided_dependency_names=route_handler.dependency_name_set,
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
