from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from functools import partial
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence, cast

from typing_extensions import Self, TypedDict

from litestar._asgi import ASGIRouter
from litestar._asgi.utils import get_route_handlers, wrap_in_exception_handler
from litestar._openapi.path_item import create_path_item
from litestar._signature import create_signature_model
from litestar.config.allowed_hosts import AllowedHostsConfig
from litestar.config.app import AppConfig
from litestar.config.response_cache import ResponseCacheConfig
from litestar.connection import Request, WebSocket
from litestar.constants import OPENAPI_NOT_INITIALIZED
from litestar.datastructures.state import State
from litestar.events.emitter import BaseEventEmitterBackend, SimpleEventEmitter
from litestar.exceptions import (
    ImproperlyConfiguredException,
    NoRouteMatchFoundException,
)
from litestar.handlers.http_handlers import HTTPRouteHandler
from litestar.logging.config import LoggingConfig, get_logger_placeholder
from litestar.middleware.cors import CORSMiddleware
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec.components import Components
from litestar.plugins import (
    InitPluginProtocol,
    OpenAPISchemaPluginProtocol,
    SerializationPluginProtocol,
)
from litestar.router import Router
from litestar.routes import ASGIRoute, HTTPRoute, WebSocketRoute
from litestar.static_files.base import StaticFiles
from litestar.stores.registry import StoreRegistry
from litestar.types import Empty
from litestar.types.internal_types import PathParameterDefinition
from litestar.utils import (
    as_async_callable_list,
    async_partial,
    is_async_callable,
    join_paths,
    unique,
)
from litestar.utils.dataclass import extract_dataclass_items
from litestar.utils.helpers import unwrap_partial
from litestar.utils.signature import ParsedSignature

if TYPE_CHECKING:
    from litestar.config.compression import CompressionConfig
    from litestar.config.cors import CORSConfig
    from litestar.config.csrf import CSRFConfig
    from litestar.datastructures import CacheControlHeader, ETag, ResponseHeader
    from litestar.dto.interface import DTOInterface
    from litestar.events.listener import EventListener
    from litestar.handlers.base import BaseRouteHandler
    from litestar.logging.config import BaseLoggingConfig
    from litestar.openapi.spec import SecurityRequirement
    from litestar.openapi.spec.open_api import OpenAPI
    from litestar.plugins import PluginProtocol
    from litestar.static_files.config import StaticFilesConfig
    from litestar.stores.base import Store
    from litestar.template.config import TemplateConfig
    from litestar.types import (
        AfterExceptionHookHandler,
        AfterRequestHookHandler,
        AfterResponseHookHandler,
        AnyCallable,
        ASGIApp,
        BeforeMessageSendHookHandler,
        BeforeRequestHookHandler,
        ControllerRouterHandler,
        Dependencies,
        EmptyType,
        ExceptionHandlersMap,
        GetLogger,
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
        OptionalSequence,
        ParametersMap,
        Receive,
        ResponseCookies,
        ResponseType,
        RouteHandlerType,
        Scope,
        Send,
        TypeEncodersMap,
    )

__all__ = ("HandlerIndex", "Litestar", "DEFAULT_OPENAPI_CONFIG")

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig(title="Litestar API", version="1.0.0")
"""The default OpenAPI config used if not configuration is explicitly passed to the
:class:`Litestar <.app.Litestar>` instance constructor.
"""


class HandlerIndex(TypedDict):
    """Map route handler names to a mapping of paths + route handler.

    It's returned from the 'get_handler_index_by_name' utility method.
    """

    paths: list[str]
    """Full route paths to the route handler."""
    handler: RouteHandlerType
    """Route handler instance."""
    identifier: str
    """Unique identifier of the handler.

    Either equal to :attr`__name__ <obj.__name__>` attribute or ``__str__`` value of the handler.
    """


class Litestar(Router):
    """The Litestar application.

    ``Litestar`` is the root level of the app - it has the base path of ``/`` and all root level Controllers, Routers
    and Route Handlers should be registered on it.
    """

    __slots__ = (
        "_debug",
        "_openapi_schema",
        "after_exception",
        "after_shutdown",
        "after_startup",
        "allowed_hosts",
        "asgi_handler",
        "asgi_router",
        "before_send",
        "before_shutdown",
        "before_startup",
        "compression_config",
        "cors_config",
        "csrf_config",
        "event_emitter",
        "get_logger",
        "logger",
        "logging_config",
        "multipart_form_part_limit",
        "signature_namespace",
        "on_shutdown",
        "on_startup",
        "openapi_config",
        "openapi_schema_plugins",
        "preferred_validation_backend",
        "request_class",
        "response_cache_config",
        "route_map",
        "serialization_plugins",
        "state",
        "static_files_config",
        "stores",
        "template_engine",
        "websocket_class",
    )

    def __init__(
        self,
        route_handlers: OptionalSequence[ControllerRouterHandler] = None,
        *,
        after_exception: OptionalSequence[AfterExceptionHookHandler] = None,
        after_request: AfterRequestHookHandler | None = None,
        after_response: AfterResponseHookHandler | None = None,
        after_shutdown: OptionalSequence[LifeSpanHookHandler] = None,
        after_startup: OptionalSequence[LifeSpanHookHandler] = None,
        allowed_hosts: Sequence[str] | AllowedHostsConfig | None = None,
        before_request: BeforeRequestHookHandler | None = None,
        before_send: OptionalSequence[BeforeMessageSendHookHandler] = None,
        before_shutdown: OptionalSequence[LifeSpanHookHandler] = None,
        before_startup: OptionalSequence[LifeSpanHookHandler] = None,
        cache_control: CacheControlHeader | None = None,
        compression_config: CompressionConfig | None = None,
        cors_config: CORSConfig | None = None,
        csrf_config: CSRFConfig | None = None,
        dto: type[DTOInterface] | None | EmptyType = Empty,
        debug: bool = False,
        dependencies: Dependencies | None = None,
        etag: ETag | None = None,
        event_emitter_backend: type[BaseEventEmitterBackend] = SimpleEventEmitter,
        exception_handlers: ExceptionHandlersMap | None = None,
        guards: OptionalSequence[Guard] = None,
        listeners: OptionalSequence[EventListener] = None,
        logging_config: BaseLoggingConfig | EmptyType | None = Empty,
        middleware: OptionalSequence[Middleware] = None,
        multipart_form_part_limit: int = 1000,
        on_app_init: OptionalSequence[OnAppInitHandler] = None,
        on_shutdown: OptionalSequence[LifeSpanHandler] = None,
        on_startup: OptionalSequence[LifeSpanHandler] = None,
        openapi_config: OpenAPIConfig | None = DEFAULT_OPENAPI_CONFIG,
        opt: Mapping[str, Any] | None = None,
        parameters: ParametersMap | None = None,
        plugins: OptionalSequence[PluginProtocol] = None,
        preferred_validation_backend: Literal["pydantic", "attrs"] | None = None,
        request_class: type[Request] | None = None,
        response_cache_config: ResponseCacheConfig | None = None,
        response_class: ResponseType | None = None,
        response_cookies: ResponseCookies | None = None,
        response_headers: OptionalSequence[ResponseHeader] = None,
        return_dto: type[DTOInterface] | None | EmptyType = Empty,
        security: OptionalSequence[SecurityRequirement] = None,
        signature_namespace: Mapping[str, Any] | None = None,
        state: State | None = None,
        static_files_config: OptionalSequence[StaticFilesConfig] = None,
        stores: StoreRegistry | dict[str, Store] | None = None,
        tags: Sequence[str] | None = None,
        template_config: TemplateConfig | None = None,
        type_encoders: TypeEncodersMap | None = None,
        websocket_class: type[WebSocket] | None = None,
    ) -> None:
        """Initialize a ``Litestar`` application.

        Args:
            after_exception: A sequence of :class:`exception hook handlers <.types.AfterExceptionHookHandler>`. This
                hook is called after an exception occurs. In difference to exception handlers, it is not meant to
                return a response - only to process the exception (e.g. log it, send it to Sentry etc.).
            after_request: A sync or async function executed after the route handler function returned and the response
                object has been resolved. Receives the response object.
            after_response: A sync or async function called after the response has been awaited. It receives the
                :class:`Request <.connection.Request>` object and should not return any values.
            after_shutdown: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
                the ASGI shutdown, after all callables in the 'on_shutdown' list have been called.
            after_startup: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
                the ASGI startup, after all callables in the 'on_startup' list have been called.
            allowed_hosts: A sequence of allowed hosts, or an
                :class:`AllowedHostsConfig <.config.allowed_hosts.AllowedHostsConfig>` instance. Enables the builtin
                allowed hosts middleware.
            before_request: A sync or async function called immediately before calling the route handler. Receives the
                :class:`Request <.connection.Request>` instance and any non-``None`` return value is used for the
                response, bypassing the route handler.
            before_send: A sequence of :class:`before send hook handlers <.types.BeforeMessageSendHookHandler>`. Called
                when the ASGI send function is called.
            before_shutdown: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
                the ASGI shutdown, before any 'on_shutdown' hooks are called.
            before_startup: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
                the ASGI startup, before any 'on_startup' hooks are called.
            cache_control: A ``cache-control`` header of type
                :class:`CacheControlHeader <litestar.datastructures.CacheControlHeader>` to add to route handlers of
                this app. Can be overridden by route handlers.
            compression_config: Configures compression behaviour of the application, this enabled a builtin or user
                defined Compression middleware.
            cors_config: If set, configures :class:`CORSMiddleware <.middleware.cors.CORSMiddleware>`.
            csrf_config: If set, configures :class:`CSRFMiddleware <.middleware.csrf.CSRFMiddleware>`.
            debug: If ``True``, app errors rendered as HTML with a stack trace.
            dependencies: A string keyed mapping of dependency :class:`Providers <.di.Provide>`.
            dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for (de)serializing and
                validation of request data.
            etag: An ``etag`` header of type :class:`ETag <.datastructures.ETag>` to add to route handlers of this app.
                Can be overridden by route handlers.
            event_emitter_backend: A subclass of
                :class:`BaseEventEmitterBackend <.events.emitter.BaseEventEmitterBackend>`.
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            listeners: A sequence of :class:`EventListener <.events.listener.EventListener>`.
            logging_config: A subclass of :class:`BaseLoggingConfig <.logging.config.BaseLoggingConfig>`.
            middleware: A sequence of :class:`Middleware <.types.Middleware>`.
            multipart_form_part_limit: The maximal number of allowed parts in a multipart/formdata request. This limit
                is intended to protect from DoS attacks.
            on_app_init: A sequence of :class:`OnAppInitHandler <.types.OnAppInitHandler>` instances. Handlers receive
                an instance of :class:`AppConfig <.config.app.AppConfig>` that will have been initially populated with
                the parameters passed to :class:`Litestar <litestar.app.Litestar>`, and must return an instance of same.
                If more than one handler is registered they are called in the order they are provided.
            on_shutdown: A sequence of :class:`LifeSpanHandler <.types.LifeSpanHandler>` called during application
                shutdown.
            on_startup: A sequence of :class:`LifeSpanHandler <litestar.types.LifeSpanHandler>` called during
                application startup.
            openapi_config: Defaults to :attr:`DEFAULT_OPENAPI_CONFIG`
            opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
                wherever you have access to :class:`Request <litestar.connection.request.Request>` or
                :class:`ASGI Scope <.types.Scope>`.
            parameters: A mapping of :class:`Parameter <.params.Parameter>` definitions available to all application
                paths.
            plugins: Sequence of plugins.
            preferred_validation_backend: Validation backend to use, if multiple are installed.
            request_class: An optional subclass of :class:`Request <.connection.Request>` to use for http connections.
            response_class: A custom subclass of :class:`Response <.response.Response>` to be used as the app's default
                response.
            response_cookies: A sequence of :class:`Cookie <.datastructures.Cookie>`.
            response_headers: A string keyed mapping of :class:`ResponseHeader <.datastructures.ResponseHeader>`
            response_cache_config: Configures caching behavior of the application.
            return_dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for serializing
                outbound response data.
            route_handlers: A sequence of route handlers, which can include instances of
                :class:`Router <.router.Router>`, subclasses of :class:`Controller <.controller.Controller>` or any
                callable decorated by the route handler decorators.
            security: A sequence of dicts that will be added to the schema of all route handlers in the application.
                See
                :data:`SecurityRequirement <.openapi.spec.SecurityRequirement>` for details.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
            state: An optional :class:`State <.datastructures.State>` for application state.
            static_files_config: A sequence of :class:`StaticFilesConfig <.static_files.StaticFilesConfig>`
            stores: Central registry of :class:`Store <.stores.base.Store>` that will be available throughout the
                application. If this is a dictionary to it will be passed to a
                :class:`StoreRegistry <.stores.registry.StoreRegistry>`. If it is a
                :class:`StoreRegistry <.stores.registry.StoreRegistry>`, this instance will be used directly.
            tags: A sequence of string tags that will be appended to the schema of all route handlers under the
                application.
            template_config: An instance of :class:`TemplateConfig <.template.TemplateConfig>`
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            websocket_class: An optional subclass of :class:`WebSocket <.connection.WebSocket>` to use for websocket
                connections.
        """
        if logging_config is Empty:
            logging_config = LoggingConfig()

        config = AppConfig(
            after_exception=list(after_exception or []),
            after_request=after_request,
            after_response=after_response,
            after_shutdown=list(after_shutdown or []),
            after_startup=list(after_startup or []),
            allowed_hosts=allowed_hosts if isinstance(allowed_hosts, AllowedHostsConfig) else list(allowed_hosts or []),
            before_request=before_request,
            before_send=list(before_send or []),
            before_shutdown=list(before_shutdown or []),
            before_startup=list(before_startup or []),
            cache_control=cache_control,
            compression_config=compression_config,
            cors_config=cors_config,
            csrf_config=csrf_config,
            debug=debug,
            dependencies=dict(dependencies or {}),
            dto=dto,
            etag=etag,
            event_emitter_backend=event_emitter_backend,
            exception_handlers=exception_handlers or {},
            guards=list(guards or []),
            listeners=list(listeners or []),
            logging_config=cast("BaseLoggingConfig | None", logging_config),
            middleware=list(middleware or []),
            multipart_form_part_limit=multipart_form_part_limit,
            on_shutdown=list(on_shutdown or []),
            on_startup=list(on_startup or []),
            openapi_config=openapi_config,
            opt=dict(opt or {}),
            parameters=parameters or {},
            plugins=list(plugins or []),
            preferred_validation_backend=preferred_validation_backend or "pydantic",
            request_class=request_class,
            response_cache_config=response_cache_config or ResponseCacheConfig(),
            response_class=response_class,
            response_cookies=response_cookies or [],
            response_headers=response_headers or [],
            return_dto=return_dto,
            route_handlers=list(route_handlers) if route_handlers is not None else [],
            security=list(security or []),
            signature_namespace=dict(signature_namespace or {}),
            state=state or State(),
            static_files_config=list(static_files_config or []),
            stores=stores,
            tags=list(tags or []),
            template_config=template_config,
            type_encoders=type_encoders,
            websocket_class=websocket_class,
        )
        for handler in chain(
            on_app_init or [],
            (p.on_app_init for p in config.plugins if isinstance(p, InitPluginProtocol)),
        ):
            config = handler(config)

        self._openapi_schema: OpenAPI | None = None
        self._debug: bool = True
        self.get_logger: GetLogger = get_logger_placeholder
        self.logger: Logger | None = None
        self.routes: list[HTTPRoute | ASGIRoute | WebSocketRoute] = []
        self.asgi_router = ASGIRouter(app=self)

        self.allowed_hosts = cast("AllowedHostsConfig | None", config.allowed_hosts)
        self.after_exception = as_async_callable_list(config.after_exception)
        self.after_shutdown = as_async_callable_list(config.after_shutdown)
        self.after_startup = as_async_callable_list(config.after_startup)
        self.allowed_hosts = cast("AllowedHostsConfig | None", config.allowed_hosts)
        self.before_send = as_async_callable_list(config.before_send)
        self.before_shutdown = as_async_callable_list(config.before_shutdown)
        self.before_startup = as_async_callable_list(config.before_startup)
        self.compression_config = config.compression_config
        self.cors_config = config.cors_config
        self.csrf_config = config.csrf_config
        self.event_emitter = config.event_emitter_backend(listeners=config.listeners)
        self.logging_config = config.logging_config
        self.multipart_form_part_limit = config.multipart_form_part_limit
        self.on_shutdown = config.on_shutdown
        self.on_startup = config.on_startup
        self.openapi_config = config.openapi_config
        self.openapi_schema_plugins = [p for p in config.plugins if isinstance(p, OpenAPISchemaPluginProtocol)]
        self.preferred_validation_backend: Literal["pydantic", "attrs"] = config.preferred_validation_backend
        self.request_class = config.request_class or Request
        self.response_cache_config = config.response_cache_config
        self.serialization_plugins = [p for p in config.plugins if isinstance(p, SerializationPluginProtocol)]
        self.state = config.state
        self.static_files_config = config.static_files_config
        self.template_engine = config.template_config.engine_instance if config.template_config else None
        self.websocket_class = config.websocket_class or WebSocket
        self.debug = config.debug

        super().__init__(
            after_request=config.after_request,
            after_response=config.after_response,
            before_request=config.before_request,
            cache_control=config.cache_control,
            dependencies=config.dependencies,
            dto=config.dto,
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
            return_dto=config.return_dto,
            # route handlers are registered below
            route_handlers=[],
            security=config.security,
            signature_namespace=config.signature_namespace,
            tags=config.tags,
            type_encoders=config.type_encoders,
        )

        for route_handler in config.route_handlers:
            self.register(route_handler)

        if self.logging_config:
            self.get_logger = self.logging_config.configure()
            self.logger = self.get_logger("litestar")

        if self.openapi_config:
            self.register(self.openapi_config.openapi_controller)

        for static_config in self.static_files_config:
            self.register(static_config.to_static_files_app())

        self.asgi_handler = self._create_asgi_handler()

        self.stores: StoreRegistry = (
            config.stores if isinstance(config.stores, StoreRegistry) else StoreRegistry(config.stores)
        )

    @property
    def debug(self) -> bool:
        return self._debug

    @debug.setter
    def debug(self, value: bool) -> None:
        if self.logger:
            self.logger.setLevel(logging.DEBUG if value else logging.INFO)
        if isinstance(self.logging_config, LoggingConfig):
            self.logging_config.loggers["litestar"]["level"] = "DEBUG" if value else "INFO"
        self._debug = value

    async def __call__(
        self,
        scope: Scope | LifeSpanScope,
        receive: Receive | LifeSpanReceive,
        send: Send | LifeSpanSend,
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

    @property
    def openapi_schema(self) -> OpenAPI:
        """Access  the OpenAPI schema of the application.

        Returns:
            The :class:`OpenAPI`
            <pydantic_openapi_schema.open_api.OpenAPI> instance of the
            application.

        Raises:
            ImproperlyConfiguredException: If the application ``openapi_config`` attribute is ``None``.
        """
        if not self.openapi_config:
            raise ImproperlyConfiguredException(OPENAPI_NOT_INITIALIZED)

        if not self._openapi_schema:
            self._openapi_schema = self.openapi_config.to_openapi_schema()
            self.update_openapi_schema()

        return self._openapi_schema

    @classmethod
    def from_config(cls, config: AppConfig) -> Self:
        """Initialize a ``Litestar`` application from a configuration instance.

        Args:
            config: An instance of :class:`AppConfig` <.config.AppConfig>

        Returns:
            An instance of ``Litestar`` application.
        """
        return cls(**dict(extract_dataclass_items(config)))

    def register(self, value: ControllerRouterHandler) -> None:  # type: ignore[override]
        """Register a route handler on the app.

        This method can be used to dynamically add endpoints to an application.

        Args:
            value: An instance of :class:`Router <.router.Router>`, a subclass of
                :class:`Controller <.controller.Controller>` or any function decorated by the route handler decorators.

        Returns:
            None
        """
        routes = super().register(value=value)

        for route in routes:
            route_handlers = get_route_handlers(route)

            for route_handler in route_handlers:
                route_handler.on_registration()
                self._set_runtime_callables(route_handler=route_handler)
                self._create_handler_signature_model(route_handler=route_handler)

            if isinstance(route, HTTPRoute):
                route.create_handler_map()

            elif isinstance(route, WebSocketRoute):
                route.handler_parameter_model = route.create_handler_kwargs_model(route.route_handler)

        self.asgi_router.construct_routing_trie()

        if self._openapi_schema is not None:
            self.update_openapi_schema()

    def get_handler_index_by_name(self, name: str) -> HandlerIndex | None:
        """Receives a route handler name and returns an optional dictionary containing the route handler instance and
        list of paths sorted lexically.

        Examples:
            .. code-block: python

                from litestar import Litestar, get

                @get("/", name="my-handler")
                def handler() -> None:
                    pass

                app = Litestar(route_handlers=[handler])

                handler_index = app.get_handler_index_by_name("my-handler")

                # { "paths": ["/"], "handler" ... }

        Args:
            name: A route handler unique name.

        Returns:
            A :class:`HandlerIndex <.app.HandlerIndex>` instance or ``None``.
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
            .. code-block: python

                from litestar import Litestar, get

                @get("/group/{group_id:int}/user/{user_id:int}", name="get_membership_details")
                def get_membership_details(group_id: int, user_id: int) -> None:
                    pass

                app = Litestar(route_handlers=[get_membership_details])

                path = app.route_reverse("get_membership_details", user_id=100, group_id=10)

                # /group/10/user/100

        Args:
            name: A route handler unique name.
            **path_parameters: Actual values for path parameters in the route.

        Raises:
            NoRouteMatchFoundException: If route with 'name' does not exist, path parameters are missing in
                ``**path_parameters or have wrong type``.

        Returns:
            A fully formatted url path.
        """
        handler_index = self.get_handler_index_by_name(name)
        if handler_index is None:
            raise NoRouteMatchFoundException(f"Route {name} can not be found")

        allow_str_instead = {datetime, date, time, timedelta, float, Path}
        output: list[str] = []

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
            .. code-block: python

                from litestar import Litestar
                from litestar.config.static_files import StaticFilesConfig

                app = Litestar(
                    static_files_config=[StaticFilesConfig(directories=["css"], path="/static/css")]
                )

                path = app.url_for_static_asset("css", "main.css")

                # /static/css/main.css

        Args:
            name: A static handler unique name.
            file_path: a string containing path to an asset.

        Raises:
            NoRouteMatchFoundException: If static files handler with ``name`` does not exist.

        Returns:
            A url path to the asset.
        """

        handler_index = self.get_handler_index_by_name(name)
        if handler_index is None:
            raise NoRouteMatchFoundException(f"Static handler {name} can not be found")

        handler_fn = cast("AnyCallable", handler_index["handler"].fn.value)
        if not isinstance(handler_fn, StaticFiles):
            raise NoRouteMatchFoundException(f"Handler with name {name} is not a static files handler")

        return join_paths([handler_index["paths"][0], file_path])  # type: ignore[unreachable]

    @property
    def route_handler_method_view(self) -> dict[str, list[str]]:
        """Map route handlers to paths.

        Returns:
            A dictionary of router handlers and lists of paths as strings
        """
        route_map: dict[str, list[str]] = {}
        for handler, routes in self.asgi_router.route_mapping.items():
            route_map[handler] = [route.path for route in routes]

        return route_map

    def _create_asgi_handler(self) -> ASGIApp:
        """Create an ASGIApp that wraps the ASGI router inside an exception handler.

        If CORS or TrustedHost configs are provided to the constructor, they will wrap the router as well.
        """
        asgi_handler: ASGIApp = self.asgi_router
        if self.cors_config:
            asgi_handler = CORSMiddleware(app=asgi_handler, config=self.cors_config)

        return wrap_in_exception_handler(
            debug=self.debug, app=asgi_handler, exception_handlers=self.exception_handlers or {}
        )

    @staticmethod
    def _set_runtime_callables(route_handler: BaseRouteHandler) -> None:
        """Optimize the ``route_handler.fn`` and any ``provider.dependency`` callables for runtime by doing the following:

        1. ensure that the ``self`` argument is preserved by binding it using partial.
        2. ensure sync functions are wrapped in AsyncCallable for sync_to_thread handlers.

        Args:
            route_handler: A route handler to process.

        Returns:
            None
        """
        from litestar.controller import Controller

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

    def _create_handler_signature_model(self, route_handler: BaseRouteHandler) -> None:
        """Create function signature models for all route handler functions and provider dependencies."""
        if not route_handler.signature_model:
            route_handler.signature_model = create_signature_model(
                dependency_name_set=route_handler.dependency_name_set,
                fn=cast("AnyCallable", route_handler.fn.value),
                plugins=self.serialization_plugins,
                preferred_validation_backend=self.preferred_validation_backend,
                parsed_signature=route_handler.parsed_fn_signature,
            )

        for provider in route_handler.resolve_dependencies().values():
            if not getattr(provider, "signature_model", None):
                provider.signature_model = create_signature_model(
                    dependency_name_set=route_handler.dependency_name_set,
                    fn=provider.dependency.value,
                    plugins=self.serialization_plugins,
                    preferred_validation_backend=self.preferred_validation_backend,
                    parsed_signature=ParsedSignature.from_fn(
                        unwrap_partial(provider.dependency.value), route_handler.resolve_signature_namespace()
                    ),
                )

    def _wrap_send(self, send: Send, scope: Scope) -> Send:
        """Wrap the ASGI send and handles any 'before send' hooks.

        Args:
            send: The ASGI send function.
            scope: The ASGI scope.

        Returns:
            An ASGI send function.
        """
        if self.before_send:

            async def wrapped_send(message: "Message") -> None:
                for hook in self.before_send:
                    await hook(message, self.state, scope)
                await send(message)

            return wrapped_send
        return send

    def update_openapi_schema(self) -> None:
        """Update the OpenAPI schema to reflect the route handlers registered on the app.

        Returns:
            None
        """
        if not self.openapi_config or not self._openapi_schema or self._openapi_schema.paths is None:
            raise ImproperlyConfiguredException("Cannot generate OpenAPI schema without initializing an OpenAPIConfig")

        operation_ids: list[str] = []

        if not self._openapi_schema.components:
            self._openapi_schema.components = Components()
            schemas = self._openapi_schema.components.schemas = {}
        elif not self._openapi_schema.components.schemas:
            schemas = self._openapi_schema.components.schemas = {}
        else:
            schemas = {}

        for route in self.routes:
            if (
                isinstance(route, HTTPRoute)
                and any(route_handler.include_in_schema for route_handler, _ in route.route_handler_map.values())
                and (route.path_format or "/") not in self._openapi_schema.paths
            ):
                path_item, created_operation_ids = create_path_item(
                    route=route,
                    create_examples=self.openapi_config.create_examples,
                    plugins=self.openapi_schema_plugins,
                    use_handler_docstrings=self.openapi_config.use_handler_docstrings,
                    operation_id_creator=self.openapi_config.operation_id_creator,
                    schemas=schemas,
                )
                self._openapi_schema.paths[route.path_format or "/"] = path_item

                for operation_id in created_operation_ids:
                    if operation_id in operation_ids:
                        raise ImproperlyConfiguredException(
                            f"operation_ids must be unique, "
                            f"please ensure the value of 'operation_id' is either not set or unique for {operation_id}"
                        )
                    operation_ids.append(operation_id)

    def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all attached listeners.

        Args:
            event_id: The ID of the event to emit, e.g ``my_event``.
            args: args to pass to the listener(s).
            kwargs: kwargs to pass to the listener(s)

        Returns:
            None
        """
        self.event_emitter.emit(event_id, *args, **kwargs)
