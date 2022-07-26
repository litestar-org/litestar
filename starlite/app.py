from typing import TYPE_CHECKING, Dict, List, Optional, Set, Type, Union, cast

from pydantic import validate_arguments
from pydantic.fields import FieldInfo
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from starlite.asgi import StarliteASGIRouter
from starlite.config import (
    CacheConfig,
    CompressionConfig,
    CORSConfig,
    CSRFConfig,
    OpenAPIConfig,
    StaticFilesConfig,
    TemplateConfig,
)
from starlite.datastructures import Cookie, ResponseHeader, State
from starlite.handlers.asgi import asgi
from starlite.handlers.http import HTTPRouteHandler
from starlite.middleware import CSRFMiddleware, ExceptionHandlerMiddleware
from starlite.middleware.compression.base import CompressionMiddleware
from starlite.plugins.base import PluginProtocol
from starlite.provide import Provide
from starlite.response import Response
from starlite.route_map import (  # pylint: disable=import-error, no-name-in-module
    RouteMap,
)
from starlite.router import Router
from starlite.routes import BaseRoute, HTTPRoute, WebSocketRoute
from starlite.signature import SignatureModelFactory
from starlite.types import (
    AfterRequestHandler,
    AfterResponseHandler,
    BeforeRequestHandler,
    ControllerRouterHandler,
    ExceptionHandler,
    Guard,
    LifeCycleHandler,
    Middleware,
)
from starlite.utils import normalize_path
from starlite.utils.templates import create_template_engine

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable
    from pydantic_openapi_schema.v3_1_0.open_api import OpenAPI
    from starlette.types import ASGIApp, Receive, Scope, Send

    from starlite.handlers.base import BaseRouteHandler
    from starlite.routes import ASGIRoute

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig(title="Starlite API", version="1.0.0")
"""OpenAPI config utilised if not explicitly declared to [Starlite][starlite.app.Starlite] instance constructor."""
DEFAULT_CACHE_CONFIG = CacheConfig()


class Starlite(Router):
    __slots__ = (
        "allowed_hosts",
        "asgi_handler",
        "asgi_router",
        "cache_config",
        "cors_config",
        "csrf_config",
        "debug",
        "compression_config",
        "openapi_schema",
        "plain_routes",
        "plugins",
        "route_map",
        "state",
        "template_engine",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
        allowed_hosts: Optional[List[str]] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        cache_config: CacheConfig = DEFAULT_CACHE_CONFIG,
        compression_config: Optional[CompressionConfig] = None,
        cors_config: Optional[CORSConfig] = None,
        csrf_config: Optional[CSRFConfig] = None,
        debug: bool = False,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Middleware]] = None,
        on_shutdown: Optional[List[LifeCycleHandler]] = None,
        on_startup: Optional[List[LifeCycleHandler]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG,
        parameters: Optional[Dict[str, FieldInfo]] = None,
        plugins: Optional[List[PluginProtocol]] = None,
        response_class: Optional[Type[Response]] = None,
        response_cookies: Optional[List[Cookie]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
        route_handlers: List[ControllerRouterHandler],
        static_files_config: Optional[Union[StaticFilesConfig, List[StaticFilesConfig]]] = None,
        template_config: Optional[TemplateConfig] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        The Starlite application.

        `Starlite` is the root level of the app - it has the base path of "/" and all root level
        Controllers, Routers and Route Handlers should be registered on it.

        It inherits from the [Router][starlite.router.Router] class.

        Args:
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            allowed_hosts: A list of allowed hosts - enables `AllowedHostsMiddleware`.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            cache_config: Configures caching behavior of the application.
            compression_config: Configures compression behaviour of the application.
            cors_config: If set this enables the `starlette.middleware.cores.CORSMiddleware`.
            csrf_config: If set this enables the CSRF middleware.
            debug: If `True`, app errors rendered as HTML with a stack trace.
            dependencies: A string/[Provider][starlite.provide.Provide] dictionary that maps dependency providers.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            middleware: A list of [Middleware][starlite.types.Middleware].
            on_shutdown: A list of [LifeCycleHandler][starlite.types.LifeCycleHandler] called during application
                shutdown.
            on_startup: A list of [LifeCycleHandler][starlite.types.LifeCycleHandler] called during application startup.
            openapi_config: Defaults to [DEFAULT_OPENAPI_CONFIG][starlite.app.DEFAULT_OPENAPI_CONFIG]
            parameters: A mapping of [Parameter][starlite.params.Parameter] definitions available to all
                application paths.
            plugins: List of plugins.
            response_class: A custom subclass of [starlite.response.Response] to be used as the app's default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            route_handlers: A required list of route handlers, which can include instances of
                [Router][starlite.router.Router], subclasses of [Controller][starlite.controller.Controller] or any
                function decorated by the route handler decorators.
            static_files_config: An instance or list of [StaticFilesConfig][starlite.config.StaticFilesConfig]
            template_config: An instance of [TemplateConfig][starlite.config.TemplateConfig]
            tags: A list of string tags that will be appended to the schema of all route handlers under the application.
        """
        self.allowed_hosts = allowed_hosts
        self.cache_config = cache_config
        self.cors_config = cors_config
        self.csrf_config = csrf_config
        self.debug = debug
        self.compression_config = compression_config
        self.plain_routes: Set[str] = set()
        self.plugins = plugins or []
        self.routes: List[BaseRoute] = []
        self.route_map = RouteMap(self.debug)
        self.state = State()

        super().__init__(
            after_request=after_request,
            after_response=after_response,
            before_request=before_request,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            parameters=parameters,
            path="",
            response_class=response_class,
            response_cookies=response_cookies,
            response_headers=response_headers,
            route_handlers=route_handlers,
            tags=tags,
        )

        self.asgi_router = StarliteASGIRouter(on_shutdown=on_shutdown or [], on_startup=on_startup or [], app=self)
        self.asgi_handler = self.create_asgi_handler()
        self.openapi_schema: Optional["OpenAPI"] = None
        if openapi_config:
            self.openapi_schema = openapi_config.create_openapi_schema_model(self)
            self.register(openapi_config.openapi_controller)
        if static_files_config:
            for config in static_files_config if isinstance(static_files_config, list) else [static_files_config]:
                path = normalize_path(config.path)
                self.route_map.add_static_path(path)
                static_files = StaticFiles(html=config.html_mode, check_dir=False)
                static_files.all_directories = config.directories  # type: ignore
                self.register(asgi(path=path)(static_files))
        self.template_engine = create_template_engine(template_config)

    def create_asgi_handler(self) -> "ASGIApp":
        """
        Creates an ASGIApp that wraps the ASGI router inside an exception handler.

        If CORS or TrustedHost configs are provided to the constructor, they will wrap the router as well.
        """
        asgi_handler: "ASGIApp" = self.asgi_router
        if self.compression_config:
            asgi_handler = CompressionMiddleware(app=asgi_handler, config=self.compression_config)
        if self.allowed_hosts:
            asgi_handler = TrustedHostMiddleware(app=asgi_handler, allowed_hosts=self.allowed_hosts)
        if self.cors_config:
            asgi_handler = CORSMiddleware(app=asgi_handler, **self.cors_config.dict())
        if self.csrf_config:
            asgi_handler = CSRFMiddleware(app=asgi_handler, config=self.csrf_config)
        return self.wrap_in_exception_handler(asgi_handler, exception_handlers=self.exception_handlers or {})

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
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
        self, app: "ASGIApp", exception_handlers: Dict[Union[int, Type[Exception]], ExceptionHandler]
    ) -> "ASGIApp":
        """
        Wraps the given ASGIApp in an instance of ExceptionHandlerMiddleware
        """

        return ExceptionHandlerMiddleware(app=app, exception_handlers=exception_handlers, debug=self.debug)

    def register(self, value: ControllerRouterHandler) -> None:  # type: ignore[override]
        """

        Registers a route handler on the app. This method can be used to dynamically add endpoints to an application.

        Args:
            value: an instance of [Router][starlite.router.Router], a subclasses of
        [Controller][starlite.controller.Controller] or any function decorated by the route handler decorators.

        Returns:
            None
        """
        routes = super().register(value=value)
        for route in routes:
            if isinstance(route, HTTPRoute):
                route_handlers = route.route_handlers
            else:
                route_handlers = [cast("Union[WebSocketRoute, ASGIRoute]", route).route_handler]  # type: ignore
            for route_handler in route_handlers:
                self.create_handler_signature_model(route_handler=route_handler)
                route_handler.resolve_guards()
                route_handler.resolve_middleware()
                if isinstance(route_handler, HTTPRouteHandler):
                    route_handler.resolve_response_class()
                    route_handler.resolve_before_request()
                    route_handler.resolve_after_request()
                    route_handler.resolve_after_response()
                    route_handler.resolve_response_headers()
                    route_handler.resolve_response_cookies()
            if isinstance(route, HTTPRoute):
                route.create_handler_map()
            elif isinstance(route, WebSocketRoute):
                route.handler_parameter_model = route.create_handler_kwargs_model(route.route_handler)
        self.route_map.add_routes(self.routes)

    def create_handler_signature_model(self, route_handler: "BaseRouteHandler") -> None:
        """
        Creates function signature models for all route handler functions and provider dependencies
        """
        if not route_handler.signature_model:
            route_handler.signature_model = SignatureModelFactory(
                fn=cast("AnyCallable", route_handler.fn),
                plugins=self.plugins,
                dependency_names=route_handler.dependency_name_set,
            ).create_signature_model()
        for provider in list(route_handler.resolve_dependencies().values()):
            if not provider.signature_model:
                provider.signature_model = SignatureModelFactory(
                    fn=provider.dependency,
                    plugins=self.plugins,
                    dependency_names=route_handler.dependency_name_set,
                ).create_signature_model()
