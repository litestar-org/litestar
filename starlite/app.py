from datetime import date, datetime, time, timedelta
from functools import partial
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from pydantic_openapi_schema import construct_open_api_with_schema_class
from typing_extensions import TypedDict

from starlite.asgi import ASGIRouter
from starlite.asgi.utils import get_route_handlers, wrap_in_exception_handler
from starlite.config import AllowedHostsConfig, AppConfig, CacheConfig, OpenAPIConfig
from starlite.config.logging import get_logger_placeholder
from starlite.connection import Request, WebSocket
from starlite.datastructures.state import ImmutableState, State
from starlite.exceptions import (
    ImproperlyConfiguredException,
    NoRouteMatchFoundException,
)
from starlite.handlers.http import HTTPRouteHandler
from starlite.middleware.cors import CORSMiddleware
from starlite.openapi.path_item import create_path_item
from starlite.router import Router
from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
from starlite.signature import SignatureModelFactory
from starlite.types.internal_types import PathParameterDefinition
from starlite.utils import (
    as_async_callable_list,
    async_partial,
    is_async_callable,
    join_paths,
    unique,
)
from starlite.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from pydantic_openapi_schema.v3_1_0 import SecurityRequirement
    from pydantic_openapi_schema.v3_1_0.open_api import OpenAPI

    from starlite.config import (
        BaseLoggingConfig,
        CompressionConfig,
        CORSConfig,
        CSRFConfig,
        StaticFilesConfig,
        TemplateConfig,
    )
    from starlite.datastructures import CacheControlHeader, ETag, Provide
    from starlite.handlers.base import BaseRouteHandler
    from starlite.plugins.base import PluginProtocol
    from starlite.types import (
        AfterExceptionHookHandler,
        AfterRequestHookHandler,
        AfterResponseHookHandler,
        ASGIApp,
        BeforeMessageSendHookHandler,
        BeforeRequestHookHandler,
        ControllerRouterHandler,
        ExceptionHandlersMap,
        Guard,
        LifeSpanHandler,
        LifeSpanHookHandler,
        LifeSpanReceive,
        LifeSpanScope,
        LifeSpanSend,
        Logger,
        Message,
        Middleware,
        OnAppInitHandler,
        ParametersMap,
        Receive,
        ResponseCookies,
        ResponseHeadersMap,
        ResponseType,
        RouteHandlerType,
        Scope,
        Send,
        SingleOrList,
        TypeEncodersMap,
    )
    from starlite.types.callable_types import AnyCallable, GetLogger

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig(title="Starlite API", version="1.0.0")
"""The default OpenAPI config used if not configuration is explicitly passed to the [Starlite][starlite.app.Starlite]
instance constructor.
"""
DEFAULT_CACHE_CONFIG = CacheConfig()
"""The default cache config used if not configuration is explicitly passed to the [Starlite][starlite.app.Starlite]
instance constructor.
"""


class HandlerIndex(TypedDict):
    """Map route handler names to a mapping of paths + route handler.

    It's returned from the 'get_handler_index_by_name' utility method.
    """

    paths: List[str]
    """Full route paths to the route handler."""
    handler: "RouteHandlerType"
    """Route handler instance."""
    identifier: str
    """Unique identifier of the handler.

    Either equal to the 'name' attribute or the __str__ value of the handler.
    """


class Starlite(Router):
    """The Starlite application.

    `Starlite` is the root level of the app - it has the base path of "/" and all root level
    Controllers, Routers and Route Handlers should be registered on it.

    Inherits from the [Router][starlite.router.Router] class
    """

    __slots__ = (
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
        "get_logger",
        "logger",
        "logging_config",
        "on_shutdown",
        "on_startup",
        "openapi_config",
        "openapi_schema",
        "plugins",
        "request_class",
        "route_map",
        "state",
        "static_files_config",
        "template_engine",
        "websocket_class",
    )

    def __init__(
        self,
        route_handlers: List["ControllerRouterHandler"],
        *,
        after_exception: Optional["SingleOrList[AfterExceptionHookHandler]"] = None,
        after_request: Optional["AfterRequestHookHandler"] = None,
        after_response: Optional["AfterResponseHookHandler"] = None,
        after_shutdown: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
        after_startup: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
        allowed_hosts: Optional[Union[List[str], "AllowedHostsConfig"]] = None,
        before_request: Optional["BeforeRequestHookHandler"] = None,
        before_send: Optional["SingleOrList[BeforeMessageSendHookHandler]"] = None,
        before_shutdown: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
        before_startup: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
        cache_config: CacheConfig = DEFAULT_CACHE_CONFIG,
        cache_control: Optional["CacheControlHeader"] = None,
        compression_config: Optional["CompressionConfig"] = None,
        cors_config: Optional["CORSConfig"] = None,
        csrf_config: Optional["CSRFConfig"] = None,
        debug: bool = False,
        dependencies: Optional[Dict[str, "Provide"]] = None,
        etag: Optional["ETag"] = None,
        exception_handlers: Optional["ExceptionHandlersMap"] = None,
        guards: Optional[List["Guard"]] = None,
        initial_state: Optional[Union["ImmutableState", Dict[str, Any], Iterable[Tuple[str, Any]]]] = None,
        logging_config: Optional["BaseLoggingConfig"] = None,
        middleware: Optional[List["Middleware"]] = None,
        on_app_init: Optional[List["OnAppInitHandler"]] = None,
        on_shutdown: Optional[List["LifeSpanHandler"]] = None,
        on_startup: Optional[List["LifeSpanHandler"]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG,
        opt: Optional[Dict[str, Any]] = None,
        parameters: Optional["ParametersMap"] = None,
        plugins: Optional[List["PluginProtocol"]] = None,
        request_class: Optional[Type["Request"]] = None,
        response_class: Optional["ResponseType"] = None,
        response_cookies: Optional["ResponseCookies"] = None,
        response_headers: Optional["ResponseHeadersMap"] = None,
        security: Optional[List["SecurityRequirement"]] = None,
        static_files_config: Optional[Union["StaticFilesConfig", List["StaticFilesConfig"]]] = None,
        tags: Optional[List[str]] = None,
        template_config: Optional["TemplateConfig"] = None,
        type_encoders: Optional["TypeEncodersMap"] = None,
        websocket_class: Optional[Type["WebSocket"]] = None,
    ) -> None:
        """Initialize a `Starlite` application.

        Args:
            after_exception: An application level [exception hook handler][starlite.types.AfterExceptionHookHandler]
                or list thereof.This hook is called after an exception occurs. In difference to exception handlers,
                it is not meant to return a response - only to process the exception (e.g. log it, send it to Sentry etc.).
            after_request: A sync or async function executed after the route handler function returned and the response
                object has been resolved. Receives the response object.
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
            cache_control: A `cache-control` header of type
                [CacheControlHeader][starlite.datastructures.CacheControlHeader] to add to route handlers of this app.
                Can be overridden by route handlers.
            compression_config: Configures compression behaviour of the application, this enabled a builtin or user
                defined Compression middleware.
            cors_config: If set this enables the builtin CORS middleware.
            csrf_config: If set this enables the builtin CSRF middleware.
            debug: If `True`, app errors rendered as HTML with a stack trace.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            etag: An `etag` header of type [ETag][starlite.datastructures.ETag] to add to route handlers of this app.
                Can be overridden by route handlers.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            initial_state: An object from which to initialize the app state.
            logging_config: A subclass of [BaseLoggingConfig][starlite.config.logging.BaseLoggingConfig].
            middleware: A list of [Middleware][starlite.types.Middleware].
            on_app_init: A sequence of [OnAppInitHandler][starlite.types.OnAppInitHandler] instances. Handlers receive
                an instance of [AppConfig][starlite.config.app.AppConfig] that will have been initially populated with
                the parameters passed to [Starlite][starlite.app.Starlite], and must return an instance of same. If more
                than one handler is registered they are called in the order they are provided.
            on_shutdown: A list of [LifeSpanHandler][starlite.types.LifeSpanHandler] called during
                application shutdown.
            on_startup: A list of [LifeSpanHandler][starlite.types.LifeSpanHandler] called during
                application startup.
            openapi_config: Defaults to [DEFAULT_OPENAPI_CONFIG][starlite.app.DEFAULT_OPENAPI_CONFIG]
            opt: A string keyed dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or wherever you
                have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            parameters: A mapping of [Parameter][starlite.params.Parameter] definitions available to all
                application paths.
            plugins: List of plugins.
            request_class: An optional subclass of [Request][starlite.connection.request.Request] to use for
                http connections.
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
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            websocket_class: An optional subclass of [WebSocket][starlite.connection.websocket.WebSocket] to use for
                websocket connections.
        """
        self.openapi_schema: Optional["OpenAPI"] = None
        self.get_logger: "GetLogger" = get_logger_placeholder
        self.logger: Optional["Logger"] = None
        self.routes: List[Union["HTTPRoute", "ASGIRoute", "WebSocketRoute"]] = []
        self.state = State(initial_state, deep_copy=True) if initial_state else State()
        self.asgi_router = ASGIRouter(app=self)

        config = AppConfig(
            after_exception=after_exception or [],
            after_request=after_request,
            after_response=after_response,
            after_shutdown=after_shutdown or [],
            after_startup=after_startup or [],
            allowed_hosts=allowed_hosts or [],
            before_request=before_request,
            before_send=before_send or [],
            before_shutdown=before_shutdown or [],
            before_startup=before_startup or [],
            cache_config=cache_config,
            cache_control=cache_control,
            compression_config=compression_config,
            cors_config=cors_config,
            csrf_config=csrf_config,
            debug=debug,
            dependencies=dependencies or {},
            etag=etag,
            exception_handlers=exception_handlers or {},
            guards=guards or [],
            logging_config=logging_config,
            middleware=middleware or [],
            on_shutdown=on_shutdown or [],
            on_startup=on_startup or [],
            openapi_config=openapi_config,
            opt=opt or {},
            parameters=parameters or {},
            plugins=plugins or [],
            request_class=request_class,
            response_class=response_class,
            response_cookies=response_cookies or [],
            response_headers=response_headers or {},
            route_handlers=route_handlers,
            security=security or [],
            static_files_config=static_files_config or [],
            tags=tags or [],
            template_config=template_config,
            type_encoders=type_encoders,
            websocket_class=websocket_class,
        )
        for handler in on_app_init or []:
            config = handler(config)

        self.allowed_hosts = cast("Optional[AllowedHostsConfig]", config.allowed_hosts)
        self.after_exception = as_async_callable_list(config.after_exception)
        self.after_shutdown = as_async_callable_list(config.after_shutdown)
        self.after_startup = as_async_callable_list(config.after_startup)
        self.before_send = as_async_callable_list(config.before_send)
        self.before_shutdown = as_async_callable_list(config.before_shutdown)
        self.before_startup = as_async_callable_list(config.before_startup)
        self.cache = config.cache_config.to_cache()
        self.compression_config = config.compression_config
        self.cors_config = config.cors_config
        self.csrf_config = config.csrf_config
        self.debug = config.debug
        self.logging_config = config.logging_config
        self.on_shutdown = config.on_shutdown
        self.on_startup = config.on_startup
        self.openapi_config = config.openapi_config
        self.plugins = config.plugins
        self.request_class = config.request_class or Request
        self.static_files_config = config.static_files_config
        self.template_engine = config.template_config.engine_instance if config.template_config else None
        self.websocket_class = config.websocket_class or WebSocket

        super().__init__(
            after_request=config.after_request,
            after_response=config.after_response,
            before_request=config.before_request,
            cache_control=config.cache_control,
            dependencies=config.dependencies,
            etag=config.etag,
            exception_handlers=config.exception_handlers,
            guards=config.guards,
            middleware=config.middleware,
            opt=config.opt,
            parameters=config.parameters,
            path="",
            response_class=config.response_class,
            response_cookies=config.response_cookies,
            response_headers=config.response_headers,
            # route handlers are registered below
            route_handlers=[],
            security=config.security,
            tags=config.tags,
            type_encoders=config.type_encoders,
        )
        for plugin in self.plugins:
            plugin.on_app_init(app=self)

        for route_handler in config.route_handlers:
            self.register(route_handler)

        if self.logging_config:
            self.get_logger = self.logging_config.configure()
            self.logger = self.get_logger("starlite")

        if self.openapi_config:
            self.openapi_schema = self.openapi_config.to_openapi_schema()
            self.update_openapi_schema()
            self.register(self.openapi_config.openapi_controller)

        for static_config in (
            self.static_files_config if isinstance(self.static_files_config, list) else [self.static_files_config]
        ):
            self.register(static_config.to_static_files_app())

        self.asgi_handler = self._create_asgi_handler()

    async def __call__(
        self,
        scope: Union["Scope", "LifeSpanScope"],
        receive: Union["Receive", "LifeSpanReceive"],
        send: Union["Send", "LifeSpanSend"],
    ) -> None:
        """Application entry point.

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
            await self.asgi_router.lifespan(receive=receive, send=send)  # type: ignore[arg-type]
            return
        scope["state"] = {}
        await self.asgi_handler(scope, receive, self._wrap_send(send=send, scope=scope))  # type: ignore[arg-type]

    def register(self, value: "ControllerRouterHandler", add_to_openapi_schema: bool = False) -> None:  # type: ignore[override]
        """Register a route handler on the app.

        This method can be used to dynamically add endpoints to an application.

        Args:
            value: an instance of [Router][starlite.router.Router], a subclass of
                [Controller][starlite.controller.Controller] or any function decorated by the route handler decorators.
            add_to_openapi_schema: Whether to add the registered route to the OpenAPI Schema. This affects only HTTP route
                handlers.

        Returns:
            None
        """
        routes = super().register(value=value)

        should_add_to_openapi_schema = False

        for route in routes:
            route_handlers = get_route_handlers(route)

            for route_handler in route_handlers:
                self._create_handler_signature_model(route_handler=route_handler)
                self._set_runtime_callables(route_handler=route_handler)
                route_handler.resolve_guards()
                route_handler.resolve_middleware()
                route_handler.resolve_opts()

                if isinstance(route_handler, HTTPRouteHandler):
                    route_handler.resolve_before_request()
                    route_handler.resolve_after_response()
                    route_handler.resolve_response_handler()
                    should_add_to_openapi_schema = add_to_openapi_schema

            if isinstance(route, HTTPRoute):
                route.create_handler_map()

            elif isinstance(route, WebSocketRoute):
                route.handler_parameter_model = route.create_handler_kwargs_model(route.route_handler)

        self.asgi_router.construct_routing_trie()

        if should_add_to_openapi_schema:
            self.update_openapi_schema()

    def get_handler_index_by_name(self, name: str) -> Optional[HandlerIndex]:
        """Receives a route handler name and returns an optional dictionary containing the route handler instance and
        list of paths sorted lexically.

        Examples:
            ```python
            from starlite import Starlite, get


            @get("/", name="my-handler")
            def handler() -> None:
                pass


            app = Starlite(route_handlers=[handler])

            handler_index = app.get_handler_index_by_name("my-handler")

            # { "paths": ["/"], "handler" ... }
            ```
        Args:
            name: A route handler unique name.

        Returns:
            A [HandlerIndex][starlite.app.HandlerIndex] instance or None.
        """
        handler = self.asgi_router.route_handler_index.get(name)
        if not handler:
            return None

        identifier = handler.name or str(handler)
        routes = self.asgi_router.route_mapping[identifier]
        paths = sorted(unique([route.path for route in routes]))

        return HandlerIndex(handler=handler, paths=paths, identifier=identifier)

    def route_reverse(self, name: str, **path_parameters: Any) -> str:
        """Receives a route handler name, path parameter values and returns url path to the handler with filled path
        parameters.

        Examples:
            ```python
            from starlite import Starlite, get


            @get("/group/{group_id:int}/user/{user_id:int}", name="get_membership_details")
            def get_membership_details(group_id: int, user_id: int) -> None:
                pass


            app = Starlite(route_handlers=[get_membership_details])

            path = app.route_reverse("get_membership_details", user_id=100, group_id=10)

            # /group/10/user/100
            ```
        Args:
            name: A route handler unique name.
            **path_parameters: Actual values for path parameters in the route.

        Raises:
            NoRouteMatchFoundException: If route with 'name' does not exist, path parameters are missing in **path_parameters or have wrong type.

        Returns:
            A fully formatted url path.
        """
        handler_index = self.get_handler_index_by_name(name)
        if handler_index is None:
            raise NoRouteMatchFoundException(f"Route {name} can not be found")

        allow_str_instead = {datetime, date, time, timedelta, float, Path}
        output: List[str] = []

        routes = sorted(
            self.asgi_router.route_mapping[handler_index["identifier"]],
            key=lambda r: len(r.path_parameters),
            reverse=True,
        )
        passed_parameters = set(path_parameters.keys())

        selected_route = routes[-1]
        for route in routes:
            if passed_parameters.issuperset({param.name for param in route.path_parameters}):
                selected_route = route
                break

        for component in selected_route.path_components:
            if isinstance(component, PathParameterDefinition):
                val = path_parameters.get(component.name)
                if not (
                    isinstance(val, component.type) or (component.type in allow_str_instead and isinstance(val, str))
                ):
                    raise NoRouteMatchFoundException(
                        f"Received type for path parameter {component.name} doesn't match declared type {component.type}"
                    )
                output.append(str(val))
            else:
                output.append(component)

        return join_paths(output)

    def url_for_static_asset(self, name: str, file_path: str) -> str:
        """Receives a static files handler name, an asset file path and returns resolved url path to the asset.

        Examples:
            ```python
            from starlite import Starlite, StaticFilesConfig

            app = Starlite(
                static_files_config=StaticFilesConfig(directories=["css"], path="/static/css")
            )

            path = app.url_for_static_asset("css", "main.css")

            # /static/css/main.css
            ```
        Args:
            name: A static handler unique name.
            file_path: a string containing path to an asset.

        Raises:
            NoRouteMatchFoundException: If static files handler with 'name' does not exist.

        Returns:
            A url path to the asset.
        """
        from starlite.static_files.base import StaticFiles

        handler_index = self.get_handler_index_by_name(name)
        if handler_index is None:
            raise NoRouteMatchFoundException(f"Static handler {name} can not be found")

        handler_fn = cast("AnyCallable", handler_index["handler"].fn.value)
        if not isinstance(handler_fn, StaticFiles):
            raise NoRouteMatchFoundException(f"Handler with name {name} is not a static files handler")

        return join_paths([handler_index["paths"][0], file_path])  # type: ignore[unreachable]

    @property
    def route_handler_method_view(self) -> Dict[str, List[str]]:
        """Map route handlers to paths.

        Returns:
            A dictionary of router handlers and lists of paths as strings
        """
        route_map: Dict[str, List[str]] = {}
        for handler, routes in self.asgi_router.route_mapping.items():
            route_map[handler] = [route.path for route in routes]

        return route_map

    def _create_asgi_handler(self) -> "ASGIApp":
        """Create an ASGIApp that wraps the ASGI router inside an exception handler.

        If CORS or TrustedHost configs are provided to the constructor, they will wrap the router as well.
        """
        asgi_handler: "ASGIApp" = self.asgi_router
        if self.cors_config:
            asgi_handler = CORSMiddleware(app=asgi_handler, config=self.cors_config)
        return wrap_in_exception_handler(
            debug=self.debug, app=asgi_handler, exception_handlers=self.exception_handlers or {}
        )

    @staticmethod
    def _set_runtime_callables(route_handler: "BaseRouteHandler") -> None:
        """Optimize the route_handler.fn and any provider.dependency callables for runtime by doing the following:

        1. ensure that the `self` argument is preserved by binding it using partial.
        2. ensure sync functions are wrapped in AsyncCallable for sync_to_thread handlers.

        Args:
            route_handler: A route handler to process.

        Returns:
            None
        """
        from starlite.controller import Controller

        if isinstance(route_handler.owner, Controller) and not hasattr(route_handler.fn.value, "func"):
            route_handler.fn.value = partial(route_handler.fn.value, route_handler.owner)

        if isinstance(route_handler, HTTPRouteHandler):
            route_handler.has_sync_callable = False
            if not is_async_callable(route_handler.fn.value):
                if route_handler.sync_to_thread:
                    route_handler.fn.value = async_partial(route_handler.fn.value)
                else:
                    route_handler.has_sync_callable = True

        for provider in route_handler.resolve_dependencies().values():
            if not is_async_callable(provider.dependency.value):
                provider.has_sync_callable = False
                if provider.sync_to_thread:
                    provider.dependency.value = async_partial(provider.dependency.value)
                else:
                    provider.has_sync_callable = True

    def _create_handler_signature_model(self, route_handler: "BaseRouteHandler") -> None:
        """Create function signature models for all route handler functions and provider dependencies."""
        if not route_handler.signature_model:
            route_handler.signature_model = SignatureModelFactory(
                fn=cast("AnyCallable", unwrap_partial(route_handler.fn.value)),
                plugins=self.plugins,
                dependency_names=route_handler.dependency_name_set,
            ).create_signature_model()

        for provider in list(route_handler.resolve_dependencies().values()):
            if not getattr(provider, "signature_model", None):
                provider.signature_model = SignatureModelFactory(
                    fn=provider.dependency.value,
                    plugins=self.plugins,
                    dependency_names=route_handler.dependency_name_set,
                ).create_signature_model()

    def _wrap_send(self, send: "Send", scope: "Scope") -> "Send":
        """Wrap the ASGI send and handles any 'before send' hooks.

        Args:
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """
        if self.before_send:

            async def wrapped_send(message: "Message") -> None:
                for hook in self.before_send:
                    if hook.num_expected_args > 2:
                        await hook(message, self.state, scope)
                    else:
                        await hook(message, self.state)
                await send(message)

            return wrapped_send
        return send

    def update_openapi_schema(self) -> None:
        """Update the OpenAPI schema to reflect the route handlers registered on the app.

        Returns:
            None
        """
        if not self.openapi_config or not self.openapi_schema or self.openapi_schema.paths is None:
            raise ImproperlyConfiguredException("Cannot generate OpenAPI schema without initializing an OpenAPIConfig")

        for route in self.routes:
            if (
                isinstance(route, HTTPRoute)
                and any(route_handler.include_in_schema for route_handler, _ in route.route_handler_map.values())
                and (route.path_format or "/") not in self.openapi_schema.paths
            ):
                self.openapi_schema.paths[route.path_format or "/"] = create_path_item(
                    route=route,
                    create_examples=self.openapi_config.create_examples,
                    plugins=self.plugins,
                    use_handler_docstrings=self.openapi_config.use_handler_docstrings,
                )
        self.openapi_schema = construct_open_api_with_schema_class(
            open_api_schema=self.openapi_schema, by_alias=self.openapi_config.by_alias
        )
