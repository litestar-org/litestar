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

from starlite.types.asgi_types import ASGIApp, Message, Method, Scope
from starlite.types.helper_types import SyncOrAsyncUnion
from starlite.types.internal_types import PathParameterDefinition, StarliteType

if TYPE_CHECKING:
    from starlite.config.app import AppConfig
    from starlite.connection.base import ASGIConnection
    from starlite.connection.request import Request
    from starlite.datastructures.state import State
    from starlite.handlers.base import BaseRouteHandler
    from starlite.handlers.http_handlers import HTTPRouteHandler
    from starlite.response.base import Response
    from starlite.types.protocols import Logger
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
LifeSpanHookHandler = Callable[[StarliteType], SyncOrAsyncUnion[None]]
OnAppInitHandler = Callable[[AppConfig], AppConfig]
OperationIDCreator = Callable[[HTTPRouteHandler, Method, List[Union[str, PathParameterDefinition]]], str]
Serializer = Callable[[Any], Any]
