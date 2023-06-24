from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    List,
    Union,
)

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from litestar.config.app import AppConfig
    from litestar.connection.base import ASGIConnection
    from litestar.connection.request import Request
    from litestar.handlers.base import BaseRouteHandler
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.response.base import Response
    from litestar.types.asgi_types import ASGIApp, Message, Method, Scope
    from litestar.types.helper_types import SyncOrAsyncUnion
    from litestar.types.internal_types import LitestarType, PathParameterDefinition
    from litestar.types.protocols import Logger

    AfterExceptionHookHandler: TypeAlias = Callable[[Exception, Scope], SyncOrAsyncUnion[None]]
    AfterRequestHookHandler: TypeAlias = Union[
        Callable[[ASGIApp], SyncOrAsyncUnion[ASGIApp]], Callable[[Response], SyncOrAsyncUnion[Response]]
    ]
    AfterResponseHookHandler: TypeAlias = Callable[[Request], SyncOrAsyncUnion[None]]
    AsyncAnyCallable: TypeAlias = Callable[..., Awaitable[Any]]
    AnyCallable: TypeAlias = Callable[..., Any]
    AnyGenerator: TypeAlias = Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]
    BeforeMessageSendHookHandler: TypeAlias = Callable[[Message, Scope], SyncOrAsyncUnion[None]]
    BeforeRequestHookHandler: TypeAlias = Callable[[Request], Union[Any, Awaitable[Any]]]
    CacheKeyBuilder: TypeAlias = Callable[[Request], str]
    ExceptionHandler: TypeAlias = Callable[[Request, Exception], Response]
    ExceptionLoggingHandler: TypeAlias = Callable[[Logger, Scope, List[str]], None]
    GetLogger: TypeAlias = Callable[..., Logger]
    Guard: TypeAlias = Callable[[ASGIConnection, BaseRouteHandler], SyncOrAsyncUnion[None]]
    LifespanHook: TypeAlias = Union[
        Callable[[LitestarType], SyncOrAsyncUnion[Any]],
        Callable[[], SyncOrAsyncUnion[Any]],
    ]
    OnAppInitHandler: TypeAlias = Callable[[AppConfig], AppConfig]
    OperationIDCreator: TypeAlias = Callable[[HTTPRouteHandler, Method, List[Union[str, PathParameterDefinition]]], str]
    Serializer: TypeAlias = Callable[[Any], Any]
else:
    AfterExceptionHookHandler: TypeAlias = Any
    AfterRequestHookHandler: TypeAlias = Any
    AfterResponseHookHandler: TypeAlias = Any
    AsyncAnyCallable: TypeAlias = Any
    AnyCallable: TypeAlias = Any
    AnyGenerator: TypeAlias = Any
    BeforeMessageSendHookHandler: TypeAlias = Any
    BeforeRequestHookHandler: TypeAlias = Any
    CacheKeyBuilder: TypeAlias = Any
    ExceptionHandler: TypeAlias = Any
    ExceptionLoggingHandler: TypeAlias = Any
    GetLogger: TypeAlias = Any
    Guard: TypeAlias = Any
    LifespanHook: TypeAlias = Any
    OnAppInitHandler: TypeAlias = Any
    OperationIDCreator: TypeAlias = Any
    Serializer: TypeAlias = Any
