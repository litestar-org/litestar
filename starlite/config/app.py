from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseConfig, BaseModel, validator
from pydantic_openapi_schema.v3_1_0 import SecurityRequirement

from starlite.connection import Request, WebSocket
from starlite.datastructures import CacheControlHeader, ETag, Provide
from starlite.plugins.base import PluginProtocol
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
    TypeEncodersMap,
)
from starlite.types.composite_types import InitialStateType

from . import AllowedHostsConfig
from .cache import CacheConfig
from .compression import CompressionConfig
from .cors import CORSConfig
from .csrf import CSRFConfig
from .logging import BaseLoggingConfig
from .openapi import OpenAPIConfig
from .static_files import StaticFilesConfig
from .template import TemplateConfig


class AppConfig(BaseModel):
    """The parameters provided to the ``Starlite`` app are used to instantiate an instance, and then the instance is
    passed to any callbacks registered to ``on_app_init`` in the order they are provided.

    The final attribute values are used to instantiate the application object.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    after_exception: SingleOrList[AfterExceptionHookHandler]
    """An application level :class:`exception hook handler <starlite.types.AfterExceptionHookHandler>` or list thereof.

    This hook is called after an exception occurs. In difference to exception handlers, it is not meant to return a
    response - only to process the exception (e.g. log it, send it to Sentry etc.).
    """
    after_request: Optional[AfterRequestHookHandler]
    """A sync or async function executed after the route handler function returned and the response object has been
    resolved.

    Receives the response object which may be any subclass of :class:`Response <starlite.response.Response>`.
    """
    after_response: Optional[AfterResponseHookHandler]
    """A sync or async function called after the response has been awaited. It receives the.

    :class:`Request <starlite.connection.Request>` object and should not return any values.
    """
    after_shutdown: SingleOrList[LifeSpanHookHandler]
    """An application level :class:`life-span hook handler <starlite.types.LifeSpanHookHandler>` or list thereof.

    This hook is called during the ASGI shutdown, after all callables in the 'on_shutdown' list have been called.
    """
    after_startup: SingleOrList[LifeSpanHookHandler]
    """An application level :class:`life-span hook handler <starlite.types.LifeSpanHookHandler>` or list thereof.

    This hook is called during the ASGI startup, after all callables in the 'on_startup' list have been called.
    """
    allowed_hosts: Optional[Union[List[str], AllowedHostsConfig]]
    """If set enables the builtin allowed hosts middleware."""
    before_request: Optional[BeforeRequestHookHandler]
    """A sync or async function called immediately before calling the route handler. Receives the.

    :class:`Request <starlite.connection.Request>` instance and any non-``None`` return value is used for the response, bypassing
    the route handler.
    """
    before_send: SingleOrList[BeforeMessageSendHookHandler]
    """An application level :class:`before send hook handler <starlite.types.BeforeMessageSendHookHandler>` or list thereof.

    This hook is called when the ASGI send function is called.
    """
    before_shutdown: SingleOrList[LifeSpanHookHandler]
    """An application level :class:`life-span hook handler <starlite.types.LifeSpanHookHandler>` or list thereof.

    This hook is called during the ASGI shutdown, before any callables in the 'on_shutdown' list have been called.
    """
    before_startup: SingleOrList[LifeSpanHookHandler]
    """An application level :class:`life-span hook handler <starlite.types.LifeSpanHookHandler>` or list thereof.

    This hook is called during the ASGI startup, before any callables in the 'on_startup' list have been called.
    """
    cache_config: CacheConfig
    """Configures caching behavior of the application."""
    cache_control: Optional[CacheControlHeader]
    """A ``cache-control`` header of type :class:`CacheControlHeader <starlite.datastructures.CacheControlHeader>` to add to route
    handlers of this app.

    Can be overridden by route handlers.
    """
    compression_config: Optional[CompressionConfig]
    """Configures compression behaviour of the application, this enabled a builtin or user defined Compression
    middleware.
    """
    cors_config: Optional[CORSConfig]
    """If set this enables the builtin CORS middleware."""
    csrf_config: Optional[CSRFConfig]
    """If set this enables the builtin CSRF middleware."""
    debug: bool
    """If ``True``, app errors rendered as HTML with a stack trace."""
    dependencies: Dict[str, Provide]
    """A string keyed dictionary of dependency :class:`Provider <starlite.datastructures.Provide>` instances."""
    etag: Optional[ETag]
    """An ``etag`` header of type :class:`ETag <starlite.datastructures.ETag>` to add to route handlers of this app.

    Can be overridden by route handlers.
    """
    exception_handlers: ExceptionHandlersMap
    """A dictionary that maps handler functions to status codes and/or exception types."""
    guards: List[Guard]
    """A list of :class:`Guard <starlite.types.Guard>` callables."""
    initial_state: InitialStateType
    """An object from which to initialize the app state."""
    logging_config: Optional[BaseLoggingConfig]
    """An instance of :class:`BaseLoggingConfig <starlite.config.logging.BaseLoggingConfig>` subclass."""
    middleware: List[Middleware]
    """A list of :class:`Middleware <starlite.types.Middleware>`."""
    on_shutdown: List[LifeSpanHandler]
    """A list of :class:`LifeSpanHandler <starlite.types.LifeSpanHandler>` called during application shutdown."""
    on_startup: List[LifeSpanHandler]
    """A list of :class:`LifeSpanHandler <starlite.types.LifeSpanHandler>` called during application startup."""
    openapi_config: Optional[OpenAPIConfig]
    """Defaults to :data:`DEFAULT_OPENAPI_CONFIG <starlite.app.DEFAULT_OPENAPI_CONFIG>`"""
    opt: Dict[str, Any]
    """A string keyed dictionary of arbitrary values that can be accessed in :class:`Guards <starlite.types.Guard>` or
    wherever you have access to :class:`Request <starlite.connection.request.Request>` or :class:`ASGI Scope <starlite.types.Scope>`.

    Can be overridden by routers and router handlers.
    """
    parameters: ParametersMap
    """A mapping of :class:`Parameter <starlite.params.Parameter>` definitions available to all application paths."""
    plugins: List[PluginProtocol]
    """List of :class:`PluginProtocol <starlite.plugins.base.PluginProtocol>`."""
    request_class: Optional[Type[Request]]
    """An optional subclass of :class:`Request <starlite.connection.request.Request>` to use for http connections."""
    response_class: Optional[ResponseType]
    """A custom subclass of [starlite.response.Response] to be used as the app's default response."""
    response_cookies: ResponseCookies
    """A list of [Cookie](starlite.datastructures.Cookie] instances."""
    response_headers: ResponseHeadersMap
    """A string keyed dictionary mapping :class:`ResponseHeader <starlite.datastructures.ResponseHeader>` instances."""
    route_handlers: List[ControllerRouterHandler]
    """A required list of route handlers, which can include instances of :class:`Router <starlite.router.Router>`, subclasses
    of.

    :class:`Controller <starlite.controller.Controller>` or any function decorated by the route handler decorators.
    """
    security: List[SecurityRequirement]
    """A list of dictionaries that will be added to the schema of all route handlers in the application. See.

    :class:`SecurityRequirement <pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement>` for details.
    """
    static_files_config: SingleOrList[StaticFilesConfig]
    """An instance or list of :class:`StaticFilesConfig <starlite.config.StaticFilesConfig>`."""
    tags: List[str]
    """A list of string tags that will be appended to the schema of all route handlers under the application."""
    template_config: Optional[TemplateConfig]
    """An instance of :class:`TemplateConfig <starlite.config.TemplateConfig>`."""
    type_encoders: Optional[TypeEncodersMap] = None
    """A mapping of types to callables that transform them into types supported for serialization."""
    websocket_class: Optional[Type[WebSocket]]
    """An optional subclass of :class:`WebSocket <starlite.connection.websocket.WebSocket>` to use for websocket connections."""
    multipart_form_part_limit: int
    """The maximal number of allowed parts in a multipart/formdata request. This limit is intended to protect from DoS attacks."""

    @validator("allowed_hosts", always=True)
    def validate_allowed_hosts(  # pylint: disable=no-self-argument
        cls, value: Optional[Union[List[str], AllowedHostsConfig]]
    ) -> Optional[AllowedHostsConfig]:
        """Normalize the allowed hosts to be a config or None.

        Args:
            value: Optional a list of hosts or allowed hosts config

        Returns:
            Optional config.
        """
        if value:
            if isinstance(value, list):
                return AllowedHostsConfig(allowed_hosts=value)
            return value
        return None
