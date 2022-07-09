from typing import Any

from starlite.datastructures import File, Redirect, State, Stream, Template

from .app import Starlite
from .config import (
    CacheConfig,
    CompressionConfig,
    CORSConfig,
    OpenAPIConfig,
    StaticFilesConfig,
    TemplateConfig,
)
from .connection import Request, WebSocket
from .controller import Controller
from .dto import DTOFactory
from .enums import (
    HttpMethod,
    MediaType,
    OpenAPIMediaType,
    RequestEncodingType,
    ScopeType,
)
from .exceptions import (
    HTTPException,
    ImproperlyConfiguredException,
    InternalServerException,
    MissingDependencyException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
    ServiceUnavailableException,
    StarLiteException,
    ValidationException,
)
from .handlers import (
    ASGIRouteHandler,
    BaseRouteHandler,
    HTTPRouteHandler,
    WebsocketRouteHandler,
    asgi,
    delete,
    get,
    patch,
    post,
    put,
    route,
    websocket,
)
from .logging import LoggingConfig, QueueListenerHandler
from .middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from .openapi.controller import OpenAPIController
from .params import Body, Dependency, Parameter
from .plugins import PluginProtocol
from .provide import Provide
from .response import Response
from .router import Router
from .routes import BaseRoute, HTTPRoute, WebSocketRoute
from .types import MiddlewareProtocol, Partial, ResponseHeader

__all__ = [
    "ASGIRouteHandler",
    "AbstractAuthenticationMiddleware",
    "AuthenticationResult",
    "BaseRoute",
    "BaseRouteHandler",
    "Body",
    "CORSConfig",
    "CacheConfig",
    "Controller",
    "DTOFactory",
    "Dependency",
    "File",
    "CompressionConfig",
    "HTTPException",
    "HTTPRoute",
    "HTTPRouteHandler",
    "HttpMethod",
    "ImproperlyConfiguredException",
    "InternalServerException",
    "LoggingConfig",
    "MediaType",
    "MiddlewareProtocol",
    "MissingDependencyException",
    "NotAuthorizedException",
    "NotFoundException",
    "OpenAPIConfig",
    "OpenAPIController",
    "OpenAPIMediaType",
    "Parameter",
    "Partial",
    "PermissionDeniedException",
    "PluginProtocol",
    "Provide",
    "QueueListenerHandler",
    "Redirect",
    "Request",
    "RequestEncodingType",
    "Response",
    "ResponseHeader",
    "Router",
    "ScopeType",
    "ServiceUnavailableException",
    "StarLiteException",
    "Starlite",
    "State",
    "StaticFilesConfig",
    "Stream",
    "Template",
    "TemplateConfig",
    "ValidationException",
    "WebSocket",
    "WebSocketRoute",
    "WebsocketRouteHandler",
    "asgi",
    "delete",
    "get",
    "patch",
    "post",
    "put",
    "route",
    "websocket",
]


_deprecated_imports = {"TestClient", "create_test_client", "create_test_request"}


# pylint: disable=import-outside-toplevel
def __getattr__(name: str) -> Any:
    """Provide lazy importing as per https://peps.python.org/pep-0562/"""
    if name not in _deprecated_imports:
        raise AttributeError(f"Module {__package__} has no attribute {name}")

    import warnings

    warnings.warn(
        f"Importing {name} from {__package__} is deprecated, use `from starlite.testing import {name}` instead",
        DeprecationWarning,
        stacklevel=2,
    )

    from . import testing

    attr = globals()[name] = getattr(testing, name)
    return attr
