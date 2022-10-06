from typing import Dict, List, Optional, Type

from pydantic import BaseConfig, BaseModel
from pydantic_openapi_schema.v3_1_0 import SecurityRequirement

from starlite.connection import Request, WebSocket
from starlite.datastructures.provide import Provide
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
)

from .cache import CacheConfig
from .compression import CompressionConfig
from .cors import CORSConfig
from .csrf import CSRFConfig
from .logging import BaseLoggingConfig
from .openapi import OpenAPIConfig
from .static_files import StaticFilesConfig
from .template import TemplateConfig


class AppConfig(BaseModel):
    """The parameters provided to the `Starlite` app are used to instantiate an
    instance, and then the instance is passed to any callbacks registered to
    `on_app_init` in the order they are provided.

    The final attribute values are used to instantiate the application
    object.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    after_exception: SingleOrList[AfterExceptionHookHandler]
    """
    An application level [exception hook handler][starlite.types.AfterExceptionHookHandler] or list thereof. This hook
    is called after an exception occurs. In difference to exception handlers, it is not meant to return a response -
    only to process the exception (e.g. log it, send it to Sentry etc.).
    """
    after_request: Optional[AfterRequestHookHandler]
    """
    A sync or async function executed after the route handler function returned and the response object has been
    resolved. Receives the response object which may be either an instance of [Response][starlite.response.Response] or
    `starlette.Response`.
    """
    after_response: Optional[AfterResponseHookHandler]
    """
    A sync or async function called after the response has been awaited. It receives the
    [Request][starlite.connection.Request] object and should not return any values.
    """
    after_shutdown: SingleOrList[LifeSpanHookHandler]
    """
    An application level [life-span hook handler][starlite.types.LifeSpanHookHandler] or list thereof. This hook is
    called during the ASGI shutdown, after all callables in the 'on_shutdown' list have been called.
    """
    after_startup: SingleOrList[LifeSpanHookHandler]
    """
    An application level [life-span hook handler][starlite.types.LifeSpanHookHandler] or list thereof. This hook is
    called during the ASGI startup, after all callables in the 'on_startup' list have been called.
    """
    allowed_hosts: List[str]
    """
    A list of allowed hosts - enables the builtin allowed hosts middleware.
    """
    before_request: Optional[BeforeRequestHookHandler]
    """
    A sync or async function called immediately before calling the route handler. Receives the
    [Request][starlite.connection.Request] instance and any non-`None` return value is used for the response, bypassing
    the route handler.
    """
    before_send: SingleOrList[BeforeMessageSendHookHandler]
    """
    An application level [before send hook handler][starlite.types.BeforeMessageSendHookHandler] or list thereof. This
    hook is called when the ASGI send function is called.
    """
    before_shutdown: SingleOrList[LifeSpanHookHandler]
    """
    An application level [life-span hook handler][starlite.types.LifeSpanHookHandler] or list thereof. This hook is
    called during the ASGI shutdown, before any callables in the 'on_shutdown' list have been called.
    """
    before_startup: SingleOrList[LifeSpanHookHandler]
    """
    An application level [life-span hook handler][starlite.types.LifeSpanHookHandler] or list thereof. This hook is
    called during the ASGI startup, before any callables in the 'on_startup' list have been called.
    """
    cache_config: CacheConfig
    """
    Configures caching behavior of the application.
    """
    compression_config: Optional[CompressionConfig]
    """
    Configures compression behaviour of the application, this enabled a builtin or user defined Compression middleware.
    """
    cors_config: Optional[CORSConfig]
    """
    If set this enables the builtin CORS middleware.
    """
    csrf_config: Optional[CSRFConfig]
    """
    If set this enables the builtin CSRF middleware.
    """
    debug: bool
    """
    If `True`, app errors rendered as HTML with a stack trace.
    """
    dependencies: Dict[str, Provide]
    """
    A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
    """
    exception_handlers: ExceptionHandlersMap
    """
    A dictionary that maps handler functions to status codes and/or exception types.
    """
    guards: List[Guard]
    """
    A list of [Guard][starlite.types.Guard] callables.
    """
    logging_config: Optional[BaseLoggingConfig]
    """
    An instance of [BaseLoggingConfig][starlite.config.logging.BaseLoggingConfig] subclass.
    """
    middleware: List[Middleware]
    """
    A list of [Middleware][starlite.types.Middleware].
    """
    on_shutdown: List[LifeSpanHandler]
    """
    A list of [LifeSpanHandler][starlite.types.LifeSpanHandler] called during application shutdown.
    """
    on_startup: List[LifeSpanHandler]
    """
    A list of [LifeSpanHandler][starlite.types.LifeSpanHandler] called during application startup.
    """
    openapi_config: Optional[OpenAPIConfig]
    """
    Defaults to [DEFAULT_OPENAPI_CONFIG][starlite.app.DEFAULT_OPENAPI_CONFIG]
    """
    parameters: ParametersMap
    """
    A mapping of [Parameter][starlite.params.Parameter] definitions available to all application paths.
    """
    plugins: List[PluginProtocol]
    """
    List of [PluginProtocol][starlite.plugins.base.PluginProtocol].
    """
    request_class: Optional[Type[Request]]
    """
    An optional subclass of [Request][starlite.connection.request.Request] to use for http connections.
    """
    response_class: Optional[ResponseType]
    """
    A custom subclass of [starlite.response.Response] to be used as the app's default response.
    """
    response_cookies: ResponseCookies
    """
    A list of [Cookie](starlite.datastructures.Cookie] instances.
    """
    response_headers: ResponseHeadersMap
    """
    A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader] instances.
    """
    route_handlers: List[ControllerRouterHandler]
    """
    A required list of route handlers, which can include instances of [Router][starlite.router.Router], subclasses of
    [Controller][starlite.controller.Controller] or any function decorated by the route handler decorators.
    """
    security: List[SecurityRequirement]
    """
    A list of dictionaries that will be added to the schema of all route handlers in the application. See
    [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement] for details.
    """
    static_files_config: SingleOrList[StaticFilesConfig]
    """
    An instance or list of [StaticFilesConfig][starlite.config.StaticFilesConfig].
    """
    tags: List[str]
    """
    A list of string tags that will be appended to the schema of all route handlers under the application.
    """
    template_config: Optional[TemplateConfig]
    """
    An instance of [TemplateConfig][starlite.config.TemplateConfig].
    """
    websocket_class: Optional[Type[WebSocket]]
    """
    An optional subclass of [WebSocket][starlite.connection.websocket.WebSocket] to use for websocket connections.
    """
