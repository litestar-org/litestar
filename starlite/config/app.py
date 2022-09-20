from typing import Dict, List, Optional, Union

from pydantic import BaseConfig, BaseModel
from pydantic_openapi_schema.v3_1_0 import SecurityRequirement

from starlite.plugins.base import PluginProtocol
from starlite.provide import Provide
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
from .openapi import OpenAPIConfig
from .static_files import StaticFilesConfig
from .template import TemplateConfig


class AppConfig(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    route_handlers: List[ControllerRouterHandler]
    after_exception: Optional[SingleOrList[AfterExceptionHookHandler]]
    after_request: Optional[AfterRequestHookHandler]
    after_response: Optional[AfterResponseHookHandler]
    after_shutdown: Optional[SingleOrList[LifeSpanHookHandler]]
    after_startup: Optional[SingleOrList[LifeSpanHookHandler]]
    allowed_hosts: Optional[List[str]]
    before_request: Optional[BeforeRequestHookHandler]
    before_send: Optional[SingleOrList[BeforeMessageSendHookHandler]]
    before_shutdown: Optional[SingleOrList[LifeSpanHookHandler]]
    before_startup: Optional[SingleOrList[LifeSpanHookHandler]]
    cache_config: CacheConfig
    compression_config: Optional[CompressionConfig]
    cors_config: Optional[CORSConfig]
    csrf_config: Optional[CSRFConfig]
    debug: bool
    dependencies: Optional[Dict[str, Provide]]
    exception_handlers: Optional[ExceptionHandlersMap]
    guards: Optional[List[Guard]]
    middleware: Optional[List[Middleware]]
    on_shutdown: Optional[List[LifeSpanHandler]]
    on_startup: Optional[List[LifeSpanHandler]]
    openapi_config: Optional[OpenAPIConfig]
    parameters: Optional[ParametersMap]
    plugins: Optional[List[PluginProtocol]]
    response_class: Optional[ResponseType]
    response_cookies: Optional[ResponseCookies]
    response_headers: Optional[ResponseHeadersMap]
    security: Optional[List[SecurityRequirement]]
    static_files_config: Optional[Union[StaticFilesConfig, List[StaticFilesConfig]]]
    tags: Optional[List[str]]
    template_config: Optional[TemplateConfig]
