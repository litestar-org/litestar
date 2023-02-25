from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Sequence

from starlite.config.allowed_hosts import AllowedHostsConfig
from starlite.config.cache import CacheConfig
from starlite.events.emitter import SimpleEventEmitter

if TYPE_CHECKING:
    from pydantic_openapi_schema.v3_1_0 import SecurityRequirement

    from starlite.config.compression import CompressionConfig
    from starlite.config.cors import CORSConfig
    from starlite.config.csrf import CSRFConfig
    from starlite.config.logging import BaseLoggingConfig
    from starlite.config.openapi import OpenAPIConfig
    from starlite.config.static_files import StaticFilesConfig
    from starlite.config.template import TemplateConfig
    from starlite.connection import Request, WebSocket
    from starlite.datastructures import CacheControlHeader, ETag, ResponseHeader
    from starlite.di import Provide
    from starlite.events.emitter import BaseEventEmitterBackend
    from starlite.events.listener import EventListener
    from starlite.plugins import PluginProtocol
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
        ResponseType,
        TypeEncodersMap,
    )
    from starlite.types.composite_types import InitialStateType


@dataclass
class AppConfig:
    """The parameters provided to the ``Starlite`` app are used to instantiate an instance, and then the instance is
    passed to any callbacks registered to ``on_app_init`` in the order they are provided.

    The final attribute values are used to instantiate the application object.
    """

    after_exception: list[AfterExceptionHookHandler] = field(default_factory=list)
    """An application level :class:`exception hook handler <starlite.types.AfterExceptionHookHandler>` or list thereof.

    This hook is called after an exception occurs. In difference to exception handlers, it is not meant to return a
    response - only to process the exception (e.g. log it, send it to Sentry etc.).
    """
    after_request: AfterRequestHookHandler | None = field(default=None)
    """A sync or async function executed after the route handler function returned and the response object has been
    resolved.

    Receives the response object which may be any subclass of :class:`Response <starlite.response.Response>`.
    """
    after_response: AfterResponseHookHandler | None = field(default=None)
    """A sync or async function called after the response has been awaited. It receives the.

    :class:`Request <starlite.connection.Request>` object and should not return any values.
    """
    after_shutdown: list[LifeSpanHookHandler] = field(default_factory=list)
    """An application level :class:`life-span hook handler <starlite.types.LifeSpanHookHandler>` or list thereof.

    This hook is called during the ASGI shutdown, after all callables in the 'on_shutdown' list have been called.
    """
    after_startup: list[LifeSpanHookHandler] = field(default_factory=list)
    """An application level :class:`life-span hook handler <starlite.types.LifeSpanHookHandler>` or list thereof.

    This hook is called during the ASGI startup, after all callables in the 'on_startup' list have been called.
    """
    allowed_hosts: list[str] | AllowedHostsConfig | None = field(default=None)
    """If set enables the builtin allowed hosts middleware."""
    before_request: BeforeRequestHookHandler | None = field(default=None)
    """A sync or async function called immediately before calling the route handler. Receives the.

    :class:`Request <starlite.connection.Request>` instance and any non-``None`` return value is used for the response, bypassing
    the route handler.
    """
    before_send: list[BeforeMessageSendHookHandler] = field(default_factory=list)
    """An application level :class:`before send hook handler <starlite.types.BeforeMessageSendHookHandler>` or list thereof.

    This hook is called when the ASGI send function is called.
    """
    before_shutdown: list[LifeSpanHookHandler] = field(default_factory=list)
    """An application level :class:`life-span hook handler <starlite.types.LifeSpanHookHandler>` or list thereof.

    This hook is called during the ASGI shutdown, before any callables in the 'on_shutdown' list have been called.
    """
    before_startup: list[LifeSpanHookHandler] = field(default_factory=list)
    """An application level :class:`life-span hook handler <starlite.types.LifeSpanHookHandler>` or list thereof.

    This hook is called during the ASGI startup, before any callables in the 'on_startup' list have been called.
    """
    cache_config: CacheConfig = field(default_factory=CacheConfig)
    """Configures caching behavior of the application."""
    cache_control: CacheControlHeader | None = field(default=None)
    """A ``cache-control`` header of type :class:`CacheControlHeader <starlite.datastructures.CacheControlHeader>` to add to route
    handlers of this app.

    Can be overridden by route handlers.
    """
    compression_config: CompressionConfig | None = field(default=None)
    """Configures compression behaviour of the application, this enabled a builtin or user defined Compression
    middleware.
    """
    cors_config: CORSConfig | None = field(default=None)
    """If set this enables the builtin CORS middleware."""
    csrf_config: CSRFConfig | None = field(default=None)
    """If set this enables the builtin CSRF middleware."""
    debug: bool = field(default=False)
    """If ``True``, app errors rendered as HTML with a stack trace."""
    dependencies: dict[str, Provide] = field(default_factory=dict)
    """A string keyed dictionary of dependency :class:`Provider <starlite.datastructures.Provide>` instances."""
    etag: ETag | None = field(default=None)
    """An ``etag`` header of type :class:`ETag <starlite.datastructures.ETag>` to add to route handlers of this app.

    Can be overridden by route handlers.
    """
    event_emitter_backend: type[BaseEventEmitterBackend] = field(default=SimpleEventEmitter)
    """A subclass of :class:`BaseEventEmitterBackend <starlite.events.emitter.BaseEventEmitterBackend>`."""
    exception_handlers: ExceptionHandlersMap = field(default_factory=dict)
    """A dictionary that maps handler functions to status codes and/or exception types."""
    guards: list[Guard] = field(default_factory=list)
    """A list of :class:`Guard <starlite.types.Guard>` callables."""
    initial_state: InitialStateType = field(default_factory=dict)
    """An object from which to initialize the app state."""
    listeners: list[EventListener] = field(default_factory=list)
    """A list of :class:`EventListener <starlite.events.listener.EventListener>`."""
    logging_config: BaseLoggingConfig | None = field(default=None)
    """An instance of :class:`BaseLoggingConfig <starlite.config.logging.BaseLoggingConfig>` subclass."""
    middleware: list[Middleware] = field(default_factory=list)
    """A list of :class:`Middleware <starlite.types.Middleware>`."""
    on_shutdown: list[LifeSpanHandler] = field(default_factory=list)
    """A list of :class:`LifeSpanHandler <starlite.types.LifeSpanHandler>` called during application shutdown."""
    on_startup: list[LifeSpanHandler] = field(default_factory=list)
    """A list of :class:`LifeSpanHandler <starlite.types.LifeSpanHandler>` called during application startup."""
    openapi_config: OpenAPIConfig | None = field(default=None)
    """Defaults to :data:`DEFAULT_OPENAPI_CONFIG <starlite.app.DEFAULT_OPENAPI_CONFIG>`"""
    opt: dict[str, Any] = field(default_factory=dict)
    """A string keyed dictionary of arbitrary values that can be accessed in :class:`Guards <starlite.types.Guard>` or
    wherever you have access to :class:`Request <starlite.connection.request.Request>` or :class:`ASGI Scope <starlite.types.Scope>`.

    Can be overridden by routers and router handlers.
    """
    parameters: ParametersMap = field(default_factory=dict)
    """A mapping of :class:`Parameter <starlite.params.Parameter>` definitions available to all application paths."""
    plugins: list[PluginProtocol] = field(default_factory=list)
    """List of :class:`SerializationPluginProtocol <starlite.plugins.base.SerializationPluginProtocol>`."""
    request_class: type[Request] | None = field(default=None)
    """An optional subclass of :class:`Request <starlite.connection.request.Request>` to use for http connections."""
    response_class: ResponseType | None = field(default=None)
    """A custom subclass of [starlite.response.Response] to be used as the app's default response."""
    response_cookies: ResponseCookies = field(default_factory=list)  # type: ignore
    """A list of [Cookie](starlite.datastructures.Cookie] instances."""
    response_headers: Sequence[ResponseHeader] = field(default_factory=list)
    """A string keyed dictionary mapping :class:`ResponseHeader <starlite.datastructures.ResponseHeader>` instances."""
    route_handlers: list[ControllerRouterHandler] = field(default_factory=list)
    """A required list of route handlers, which can include instances of :class:`Router <starlite.router.Router>`, subclasses
    of.

    :class:`Controller <starlite.controller.Controller>` or any function decorated by the route handler decorators.
    """
    security: list[SecurityRequirement] = field(default_factory=list)
    """A list of dictionaries that will be added to the schema of all route handlers in the application. See.

    :class:`SecurityRequirement <pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement>` for details.
    """
    static_files_config: list[StaticFilesConfig] = field(default_factory=list)
    """An instance or list of :class:`StaticFilesConfig <starlite.config.StaticFilesConfig>`."""
    tags: list[str] = field(default_factory=list)
    """A list of string tags that will be appended to the schema of all route handlers under the application."""
    template_config: TemplateConfig | None = field(default=None)
    """An instance of :class:`TemplateConfig <starlite.config.TemplateConfig>`."""
    type_encoders: TypeEncodersMap | None = field(default=None)
    """A mapping of types to callables that transform them into types supported for serialization."""
    websocket_class: type[WebSocket] | None = field(default=None)
    """An optional subclass of :class:`WebSocket <starlite.connection.websocket.WebSocket>` to use for websocket connections."""
    multipart_form_part_limit: int = field(default=1000)
    """The maximal number of allowed parts in a multipart/formdata request. This limit is intended to protect from DoS attacks."""

    def __post_init__(self) -> None:
        """Normalize the allowed hosts to be a config or None.

        Returns:
            Optional config.
        """
        if self.allowed_hosts and isinstance(self.allowed_hosts, list):
            self.allowed_hosts = AllowedHostsConfig(allowed_hosts=self.allowed_hosts)
