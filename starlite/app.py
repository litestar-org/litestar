from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Union, cast

from pydantic import validate_arguments
from pydantic_openapi_schema.v3_1_0 import SecurityRequirement
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from typing_extensions import TypedDict

from starlite.asgi import (
    PathParameterTypePathDesignator,
    PathParamNode,
    RouteMapNode,
    StarliteASGIRouter,
)
from starlite.config import (
    CacheConfig,
    CompressionConfig,
    CORSConfig,
    CSRFConfig,
    OpenAPIConfig,
    StaticFilesConfig,
    TemplateConfig,
)
from starlite.datastructures import State
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.asgi import asgi
from starlite.handlers.http import HTTPRouteHandler
from starlite.middleware.compression.base import CompressionMiddleware
from starlite.middleware.csrf import CSRFMiddleware
from starlite.middleware.exceptions import ExceptionHandlerMiddleware
from starlite.plugins.base import PluginProtocol
from starlite.provide import Provide
from starlite.router import Router
from starlite.routes import ASGIRoute, BaseRoute, HTTPRoute, WebSocketRoute
from starlite.signature import SignatureModelFactory
from starlite.types import (
    AfterExceptionHookHandler,
    AfterRequestHookHandler,
    AfterResponseHookHandler,
    BeforeMessageSendHookHandler,
    BeforeRequestHookHandler,
    ControllerRouterHandler,
    ExceptionHandlersMap,
    Guard,
    LifeSpanHandler,
    LifeSpanHookHandler,
    Middleware,
    ParametersMap,
    ResponseCookies,
    ResponseHeadersMap,
    ResponseType,
    SingleOrList,
)
from starlite.utils.sync import as_async_callable_list
from starlite.utils.templates import create_template_engine

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable
    from pydantic_openapi_schema.v3_1_0.open_api import OpenAPI

    from starlite.asgi import ComponentsSet, PathParamPlaceholderType
    from starlite.handlers.asgi import ASGIRouteHandler
    from starlite.handlers.base import BaseRouteHandler
    from starlite.handlers.websocket import WebsocketRouteHandler
    from starlite.routes.base import PathParameterDefinition
    from starlite.types import ASGIApp, Message, Receive, Scope, Send

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig(title="Starlite API", version="1.0.0")
"""
    The default OpenAPI config used if not configuration is explicitly passed
    to the [Starlite][starlite.app.Starlite] instance constructor.
"""
DEFAULT_CACHE_CONFIG = CacheConfig()
"""
    The default cache config used if not configuration is explicitly passed
    to the [Starlite][starlite.app.Starlite] instance constructor.
"""


class HandlerIndex(TypedDict):
    """This class is used to map route handler names to a mapping of path +
    route handler.

    It's used in the 'get_handler_index_by_name' utility method.
    """

    path: str
    """Full route path to the route handler."""
    handler: Union["HTTPRouteHandler", "WebsocketRouteHandler", "ASGIRouteHandler"]
    """Route handler instance."""


class Starlite(Router):
    __slots__ = (
        "_init",
        "_registered_routes",
        "_route_handler_index",
        "_static_paths",
        "after_exception",
        "after_shutdown",
        "after_startup",
        "allowed_hosts",
        "asgi_handler",
        "asgi_router",
        "before_send",
        "before_shutdown",
        "before_startup",
        "cache",
        "compression_config",
        "cors_config",
        "csrf_config",
        "debug",
        "on_shutdown",
        "on_startup",
        "openapi_config",
        "openapi_schema",
        "plain_routes",
        "plugins",
        "route_map",
        "state",
        "static_files_config",
        "template_engine",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        route_handlers: List[ControllerRouterHandler],
        *,
        after_exception: Optional[SingleOrList[AfterExceptionHookHandler]] = None,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        after_shutdown: Optional[SingleOrList[LifeSpanHookHandler]] = None,
        after_startup: Optional[SingleOrList[LifeSpanHookHandler]] = None,
        allowed_hosts: Optional[List[str]] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        before_send: Optional[SingleOrList[BeforeMessageSendHookHandler]] = None,
        before_shutdown: Optional[SingleOrList[LifeSpanHookHandler]] = None,
        before_startup: Optional[SingleOrList[LifeSpanHookHandler]] = None,
        cache_config: CacheConfig = DEFAULT_CACHE_CONFIG,
        compression_config: Optional[CompressionConfig] = None,
        cors_config: Optional[CORSConfig] = None,
        csrf_config: Optional[CSRFConfig] = None,
        debug: bool = False,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Middleware]] = None,
        on_shutdown: Optional[List[LifeSpanHandler]] = None,
        on_startup: Optional[List[LifeSpanHandler]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG,
        parameters: Optional[ParametersMap] = None,
        plugins: Optional[List[PluginProtocol]] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        security: Optional[List[SecurityRequirement]] = None,
        static_files_config: Optional[Union[StaticFilesConfig, List[StaticFilesConfig]]] = None,
        tags: Optional[List[str]] = None,
        template_config: Optional[TemplateConfig] = None,
    ):
        """The Starlite application.

        `Starlite` is the root level of the app - it has the base path of "/" and all root level
        Controllers, Routers and Route Handlers should be registered on it.

        It inherits from the [Router][starlite.router.Router] class.

        Args:
            after_exception: An application level [exception hook handler][starlite.types.AfterExceptionHookHandler]
                or list thereof.This hook is called after an exception occurs. In difference to exception handlers,
                it is not meant to return a response - only to process the exception (e.g. log it, send it to Sentry etc.).
            after_request: A sync or async function executed after the route handler function returned and the response
                object has been resolved. Receives the response object which may be either an instance of
                [Response][starlite.response.Response] or `starlette.Response`.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            after_shutdown: An application level [life-span hook handler][starlite.types.LifeSpanHookHandler] or
                list thereof. This hook is called during the ASGI shutdown, after all callables in the 'on_shutdown'
                list have been called.
            after_startup: An application level [life-span hook handler][starlite.types.LifeSpanHookHandler] or
                list thereof. This hook is called during the ASGI startup, after all callables in the 'on_startup'
                list have been called.
            allowed_hosts: A list of allowed hosts - enables the builtin allowed hosts middleware.
            before_request: A sync or async function called immediately before calling the route handler.
                Receives the [Request][starlite.connection.Request] instance and any non-`None` return value is
                used for the response, bypassing the route handler.
            before_send: An application level [before send hook handler][starlite.types.BeforeMessageSendHookHandler] or
                list thereof. This hook is called when the ASGI send function is called.
            before_shutdown: An application level [life-span hook handler][starlite.types.LifeSpanHookHandler] or
                list thereof. This hook is called during the ASGI shutdown, before any callables in the 'on_shutdown'
                list have been called.
            before_startup: An application level [life-span hook handler][starlite.types.LifeSpanHookHandler] or
                list thereof. This hook is called during the ASGI startup, before any callables in the 'on_startup'
                list have been called.
            cache_config: Configures caching behavior of the application.
            compression_config: Configures compression behaviour of the application, this enabled a builtin or user
                defined Compression middleware.
            cors_config: If set this enables the builtin CORS middleware.
            csrf_config: If set this enables the builtin CSRF middleware.
            debug: If `True`, app errors rendered as HTML with a stack trace.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.provide.Provide] instances.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            middleware: A list of [Middleware][starlite.types.Middleware].
            on_shutdown: A list of [LifeSpanHandler][starlite.types.LifeSpanHandler] called during
                application shutdown.
            on_startup: A list of [LifeSpanHandler][starlite.types.LifeSpanHandler] called during
                application startup.
            openapi_config: Defaults to [DEFAULT_OPENAPI_CONFIG][starlite.app.DEFAULT_OPENAPI_CONFIG]
            parameters: A mapping of [Parameter][starlite.params.Parameter] definitions available to all
                application paths.
            plugins: List of plugins.
            response_class: A custom subclass of [starlite.response.Response] to be used as the app's default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            route_handlers: A required list of route handlers, which can include instances of
                [Router][starlite.router.Router], subclasses of [Controller][starlite.controller.Controller] or
                any function decorated by the route handler decorators.
            security: A list of dictionaries that will be added to the schema of all route handlers in the application.
                See [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement] for details.
            static_files_config: An instance or list of [StaticFilesConfig][starlite.config.StaticFilesConfig]
            tags: A list of string tags that will be appended to the schema of all route handlers under the application.
            template_config: An instance of [TemplateConfig][starlite.config.TemplateConfig]
        """

        self._init = False
        self._registered_routes: Set[BaseRoute] = set()
        self._route_handler_index: Dict[str, HandlerIndex] = {}
        self._static_paths: Set[str] = set()
        self.after_exception = as_async_callable_list(after_exception) if after_exception else []
        self.after_shutdown = as_async_callable_list(after_shutdown) if after_shutdown else []
        self.after_startup = as_async_callable_list(after_startup) if after_startup else []
        self.allowed_hosts = allowed_hosts
        self.before_send = as_async_callable_list(before_send) if before_send else []
        self.before_shutdown = as_async_callable_list(before_shutdown) if before_shutdown else []
        self.before_startup = as_async_callable_list(before_startup) if before_startup else []
        self.cache = cache_config.to_cache()
        self.compression_config = compression_config
        self.cors_config = cors_config
        self.csrf_config = csrf_config
        self.debug = debug
        self.on_shutdown = on_shutdown or []
        self.on_startup = on_startup or []
        self.openapi_config = openapi_config
        self.openapi_schema: Optional["OpenAPI"] = None
        self.plain_routes: Set[str] = set()
        self.plugins = plugins or []
        self.route_map: RouteMapNode = {}
        self.routes: List[BaseRoute] = []
        self.state = State()
        self.static_files_config = static_files_config
        self.template_engine = create_template_engine(template_config)
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
            security=security,
            tags=tags,
        )
        self._init = True

        for plugin in self.plugins:
            plugin.on_app_init(app=self)

        for route_handler in route_handlers:
            self.register(route_handler)

        if self.openapi_config:
            self.openapi_schema = self.openapi_config.create_openapi_schema_model(self)
            self.register(self.openapi_config.openapi_controller)
        if self.static_files_config:
            for config in (
                self.static_files_config if isinstance(self.static_files_config, list) else [self.static_files_config]
            ):
                self._static_paths.add(config.path)
                self.register(asgi(path=config.path)(config.to_static_files_app()))

        self.asgi_router = StarliteASGIRouter(on_shutdown=self.on_shutdown, on_startup=self.on_startup, app=self)
        self.asgi_handler = self._create_asgi_handler()

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """The application entry point.

        Lifespan events (startup / shutdown) are sent to the lifespan handler, otherwise the ASGI handler is used

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        scope["app"] = self
        if scope["type"] == "lifespan":
            await self.asgi_router.lifespan(scope, receive, send)
            return
        scope["state"] = {}
        await self.asgi_handler(scope, receive, self._wrap_send(send))

    def register(self, value: ControllerRouterHandler) -> None:  # type: ignore[override]
        """Registers a route handler on the app. This method can be used to
        dynamically add endpoints to an application.

        Args:
            value: an instance of [Router][starlite.router.Router], a subclasses of
        [Controller][starlite.controller.Controller] or any function decorated by the route handler decorators.

        Returns:
            None
        """
        if not self._init:
            return
        routes = super().register(value=value)
        for route in routes:
            if isinstance(route, HTTPRoute):
                route_handlers = route.route_handlers
            else:
                route_handlers = [cast("Union[WebSocketRoute, ASGIRoute]", route).route_handler]  # type: ignore
            for route_handler in route_handlers:

                self._create_handler_signature_model(route_handler=route_handler)
                route_handler.resolve_guards()
                route_handler.resolve_middleware()
                if isinstance(route_handler, HTTPRouteHandler):
                    route_handler.resolve_before_request()
                    route_handler.resolve_after_response()
                    route_handler.resolve_response_handler()
            if isinstance(route, HTTPRoute):
                route.create_handler_map()
            elif isinstance(route, WebSocketRoute):
                route.handler_parameter_model = route.create_handler_kwargs_model(route.route_handler)
        self._construct_route_map()

    def get_handler_index_by_name(self, name: str) -> Optional[HandlerIndex]:
        """Receives a route handler name and returns an optional dictionary
        containing the route handler instance and the path.

        Examples:
            ```python
            from starlite import Starlite, get


            @get("/", name="my-handler")
            def handler() -> None:
                pass


            app = Starlite(route_handlers=[handler])

            handler_index = app.get_handler_index_by_name("my-handler")

            # { "path": "/", "handler" ... }
            ```
        Args:
            name: A route handler unique name.

        Returns:
            A [HandlerIndex][starlite.app.HandlerIndex] instance or None.
        """
        return self._route_handler_index.get(name)

    def _create_asgi_handler(self) -> "ASGIApp":
        """Creates an ASGIApp that wraps the ASGI router inside an exception
        handler.

        If CORS or TrustedHost configs are provided to the constructor,
        they will wrap the router as well.
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
        return self._wrap_in_exception_handler(asgi_handler, exception_handlers=self.exception_handlers or {})

    def _wrap_in_exception_handler(self, app: "ASGIApp", exception_handlers: ExceptionHandlersMap) -> "ASGIApp":
        """Wraps the given ASGIApp in an instance of
        ExceptionHandlerMiddleware."""
        return ExceptionHandlerMiddleware(app=app, exception_handlers=exception_handlers, debug=self.debug)

    def _add_node_to_route_map(self, route: BaseRoute) -> RouteMapNode:
        """Adds a new route path (e.g. '/foo/bar/{param:int}') into the
        route_map tree.

        Inserts non-parameter paths ('plain routes') off the tree's root
        node. For paths containing parameters, splits the path on '/'
        and nests each path segment under the previous segment's node
        (see prefix tree / trie).
        """
        current_node = self.route_map
        path = route.path

        if route.path_parameters or path in self._static_paths:
            components = cast(
                "List[Union[str, PathParamPlaceholderType, PathParameterDefinition]]", ["/", *route.path_components]
            )
            for component in components:
                components_set = cast("ComponentsSet", current_node["_components"])

                if isinstance(component, dict):
                    # The rest of the path should be regarded as a parameter value.
                    if component["type"] is Path:
                        components_set.add(PathParameterTypePathDesignator)
                    # Represent path parameters using a special value
                    component = PathParamNode

                components_set.add(component)

                if component not in current_node:
                    current_node[component] = {"_components": set()}
                current_node = cast("RouteMapNode", current_node[component])
                if "_static_path" in current_node:
                    raise ImproperlyConfiguredException("Cannot have configured routes below a static path")
        else:
            if path not in self.route_map:
                self.route_map[path] = {"_components": set()}
            self.plain_routes.add(path)
            current_node = self.route_map[path]
        self._configure_route_map_node(route, current_node)
        return current_node

    def _add_route_to_handler_index(self, route: BaseRoute) -> None:
        """Maps route handler names to urls.

        Args:
            route: A Route instance.

        Returns:
            None
        """
        route_handlers: List[Union["HTTPRouteHandler", "WebsocketRouteHandler", "ASGIRouteHandler"]] = []
        if isinstance(route, (WebSocketRoute, ASGIRoute)):
            route_handlers.append(route.route_handler)
        else:
            route_handlers.extend(cast("HTTPRoute", route).route_handlers)

        for route_handler in route_handlers:
            if route_handler.name in self._route_handler_index:
                raise ImproperlyConfiguredException(
                    f"route handler names must be unique - {route_handler.name} is not unique."
                )
            if route_handler.name:
                self._route_handler_index[route_handler.name] = HandlerIndex(path=route.path, handler=route_handler)

    def _configure_route_map_node(self, route: BaseRoute, node: RouteMapNode) -> None:
        """Set required attributes and route handlers on route_map tree
        node."""
        if "_path_parameters" not in node:
            node["_path_parameters"] = route.path_parameters
        if "_asgi_handlers" not in node:
            node["_asgi_handlers"] = {}
        if "_is_asgi" not in node:
            node["_is_asgi"] = False
        if route.path in self._static_paths:
            if node["_components"]:
                raise ImproperlyConfiguredException("Cannot have configured routes below a static path")
            node["_static_path"] = route.path
            node["_is_asgi"] = True
        asgi_handlers = cast("Dict[str, ASGIApp]", node["_asgi_handlers"])
        if isinstance(route, HTTPRoute):
            for method, handler_mapping in route.route_handler_map.items():
                handler, _ = handler_mapping
                asgi_handlers[method] = self._build_route_middleware_stack(route, handler)
        elif isinstance(route, WebSocketRoute):
            asgi_handlers["websocket"] = self._build_route_middleware_stack(route, route.route_handler)
        elif isinstance(route, ASGIRoute):
            asgi_handlers["asgi"] = self._build_route_middleware_stack(route, route.route_handler)
            node["_is_asgi"] = True

    def _construct_route_map(self) -> None:
        """Create a map of the app's routes.

        This map is used in the asgi router to route requests.
        """
        if "_components" not in self.route_map:
            self.route_map["_components"] = set()
        new_routes = [route for route in self.routes if route not in self._registered_routes]
        for route in new_routes:
            node = self._add_node_to_route_map(route)
            if node["_path_parameters"] != route.path_parameters:
                raise ImproperlyConfiguredException("Should not use routes with conflicting path parameters")
            self._add_route_to_handler_index(route)
            self._registered_routes.add(route)

    def _build_route_middleware_stack(
        self,
        route: Union[HTTPRoute, WebSocketRoute, ASGIRoute],
        route_handler: Union["HTTPRouteHandler", "WebsocketRouteHandler", "ASGIRouteHandler"],
    ) -> "ASGIApp":
        """Constructs a middleware stack that serves as the point of entry for
        each route."""

        # we wrap the route.handle method in the ExceptionHandlerMiddleware
        asgi_handler = self._wrap_in_exception_handler(
            app=route.handle, exception_handlers=route_handler.resolve_exception_handlers()
        )

        for middleware in route_handler.resolve_middleware():
            if isinstance(middleware, StarletteMiddleware):
                handler, kwargs = middleware
                asgi_handler = handler(app=asgi_handler, **kwargs)
            else:
                asgi_handler = middleware(app=asgi_handler)

        # we wrap the entire stack again in ExceptionHandlerMiddleware
        return self._wrap_in_exception_handler(
            app=asgi_handler, exception_handlers=route_handler.resolve_exception_handlers()
        )

    def _create_handler_signature_model(self, route_handler: "BaseRouteHandler") -> None:
        """Creates function signature models for all route handler functions
        and provider dependencies."""
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

    def _wrap_send(self, send: "Send") -> "Send":
        """Wraps the ASGI send and handles any 'before send' hooks.

        Args:
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """
        if self.before_send:

            async def wrapped_send(message: "Message") -> None:
                for hook in self.before_send:
                    await hook(message, self.state)
                await send(message)

            return wrapped_send
        return send
