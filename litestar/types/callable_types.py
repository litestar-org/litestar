from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    List,
    TypeVar,
    Union,
)

from litestar.types.asgi_types import ASGIApp, Message, Method, Scope
from litestar.types.helper_types import SyncOrAsyncUnion
from litestar.types.internal_types import LitestarType, PathParameterDefinition

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.connection.base import ASGIConnection
    from litestar.connection.request import Request
    from litestar.datastructures.state import State
    from litestar.handlers.base import BaseRouteHandler
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.response.base import Response
    from litestar.types.protocols import Logger
else:
    AppConfig = Any
    BaseRouteHandler = Any
    Request = Any
    Response = Any
    State = Any
    ASGIConnection = Any
    Logger = Any
    HTTPRouteHandler = Any

ExceptionT = TypeVar("ExceptionT", bound=Exception)
AfterExceptionHookHandler = Callable[[Exception, Scope, State], SyncOrAsyncUnion[None]]
AfterRequestHookHandler = Union[
    Callable[[ASGIApp], SyncOrAsyncUnion[ASGIApp]], Callable[[Response], SyncOrAsyncUnion[Response]]
]
AfterResponseHookHandler = Callable[[Request], SyncOrAsyncUnion[None]]
AsyncAnyCallable = Callable[..., Awaitable[Any]]
AnyCallable = Callable[..., Any]
AnyGenerator = Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]
BeforeMessageSendHookHandler = Callable[[Message, State, Scope], SyncOrAsyncUnion[None]]
BeforeRequestHookHandler = Callable[[Request], Union[Any, Awaitable[Any]]]
CacheKeyBuilder = Callable[[Request], str]
ExceptionHandler = Callable[[Request, ExceptionT], Response]
ExceptionLoggingHandler = Callable[[Logger, Scope, List[str]], None]
GetLogger = Callable[..., Logger]
Guard = Callable[[ASGIConnection, BaseRouteHandler], SyncOrAsyncUnion[None]]
LifeSpanHandler = Union[Callable[[], SyncOrAsyncUnion[Any]], Callable[[State], SyncOrAsyncUnion[Any]]]
LifeSpanHookHandler = Callable[[LitestarType], SyncOrAsyncUnion[None]]
OnAppInitHandler = Callable[[AppConfig], AppConfig]
OperationIDCreator = Callable[[HTTPRouteHandler, Method, List[Union[str, PathParameterDefinition]]], str]
Serializer = Callable[[Any], Any]
