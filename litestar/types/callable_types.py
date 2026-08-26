from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar, Union

from typing_extensions import TypeAliasType

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.config.app import AppConfig
    from litestar.connection.base import ASGIConnection
    from litestar.connection.request import Request
    from litestar.handlers.base import BaseRouteHandler
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.response.base import Response
    from litestar.types.asgi_types import ASGIApp, Message, Method, Scope
    from litestar.types.helper_types import SyncOrAsyncUnion
    from litestar.types.internal_types import PathParameterDefinition
    from litestar.types.protocols import Logger

ExceptionT = TypeVar("ExceptionT", bound=Exception)

AfterExceptionHookHandler = TypeAliasType(
    "AfterExceptionHookHandler", "Callable[[ExceptionT, Scope], SyncOrAsyncUnion[None]]", type_params=(ExceptionT,)
)
AsyncAfterRequestHookHandler: TypeAlias = (
    "Callable[[ASGIApp], Awaitable[ASGIApp]] | Callable[[Response], Awaitable[Response]]"
)
SyncAfterRequestHookHandler: TypeAlias = "Callable[[ASGIApp], ASGIApp] | Callable[[Response], Response]"
AfterRequestHookHandler = TypeAliasType(
    "AfterRequestHookHandler",
    Union[AsyncAfterRequestHookHandler, SyncAfterRequestHookHandler],
)

AsyncAfterResponseHookHandler: TypeAlias = "Callable[[Request], Awaitable[None]]"
SyncAfterResponseHookHandler: TypeAlias = "Callable[[Request], None]"
AfterResponseHookHandler = TypeAliasType(
    "AfterResponseHookHandler", Union[AsyncAfterResponseHookHandler, SyncAfterResponseHookHandler]
)

AsyncBeforeRequestHookHandler = TypeAliasType("AsyncBeforeRequestHookHandler", "Callable[[Request], Awaitable[Any]]")
BeforeRequestHookHandler = TypeAliasType("BeforeRequestHookHandler", "Callable[[Request], Any | Awaitable[Any]]")


AsyncAnyCallable = TypeAliasType("AsyncAnyCallable", Callable[..., Awaitable[Any]])
AnyCallable = TypeAliasType("AnyCallable", Callable[..., Any])
AnyGenerator = TypeAliasType("AnyGenerator", Generator[Any, Any, Any] | AsyncGenerator[Any, Any])
BeforeMessageSendHookHandler = TypeAliasType(
    "BeforeMessageSendHookHandler", "Callable[[Message, Scope], SyncOrAsyncUnion[None]]"
)
CacheKeyBuilder = TypeAliasType("CacheKeyBuilder", "Callable[[Request], str]")
ExceptionHandler = TypeAliasType(
    "ExceptionHandler", "Callable[[Request, ExceptionT], Response]", type_params=(ExceptionT,)
)
ExceptionLoggingHandler = TypeAliasType("ExceptionLoggingHandler", "Callable[[Logger, Scope, list[str]], None]")
GetLogger = TypeAliasType("GetLogger", "Callable[..., Logger]")
AsyncGuard: TypeAlias = "Callable[[ASGIConnection, BaseRouteHandler], Awaitable[None]]"
SyncGuard: TypeAlias = "Callable[[ASGIConnection, BaseRouteHandler], None]"
Guard = TypeAliasType("Guard", Union[AsyncGuard, SyncGuard])
LifespanHook = TypeAliasType(
    "LifespanHook", "Callable[[Litestar], SyncOrAsyncUnion[Any]] | Callable[[], SyncOrAsyncUnion[Any]]"
)
OnAppInitHandler = TypeAliasType("OnAppInitHandler", "Callable[[AppConfig], AppConfig]")
OperationIDCreator = TypeAliasType(
    "OperationIDCreator", "Callable[[HTTPRouteHandler, Method, list[str | PathParameterDefinition]], str]"
)
Serializer = TypeAliasType("Serializer", Callable[[Any], Any])
HTTPHandlerDecorator = TypeAliasType("HTTPHandlerDecorator", "Callable[..., Callable[[AnyCallable], HTTPRouteHandler]]")
