from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    TypeVar,
    Union,
)

from .asgi_types import ASGIApp, Message, Scope
from .helper_types import SyncOrAsyncUnion
from .internal_types import StarliteType

if TYPE_CHECKING:
    from starlite.config import AppConfig
    from starlite.connection import ASGIConnection, Request
    from starlite.datastructures.state import State
    from starlite.handlers import BaseRouteHandler
    from starlite.response import Response
    from starlite.types.protocols import Logger
else:
    AppConfig = Any
    BaseRouteHandler = Any
    Request = Any
    Response = Any
    State = Any
    ASGIConnection = Any
    Logger = Any

_ExceptionT = TypeVar("_ExceptionT", bound=Exception)

AfterExceptionHookHandler = Callable[[Exception, Scope, State], SyncOrAsyncUnion[None]]
AfterRequestHookHandler = Union[
    Callable[[ASGIApp], SyncOrAsyncUnion[ASGIApp]], Callable[[Response], SyncOrAsyncUnion[Response]]
]
AfterResponseHookHandler = Callable[[Request], SyncOrAsyncUnion[None]]
AsyncAnyCallable = Callable[..., Awaitable[Any]]
AnyCallable = Callable[..., Any]
AnyGenerator = Union[Generator[Any, Any, Any], AsyncGenerator[Any, Any]]
BeforeMessageSendHookHandler = Union[
    Callable[[Message, State, Scope], SyncOrAsyncUnion[None]], Callable[[Message, State], SyncOrAsyncUnion[None]]
]
BeforeRequestHookHandler = Callable[[Request], Union[Any, Awaitable[Any]]]
CacheKeyBuilder = Callable[[Request], str]
ExceptionHandler = Callable[[Request, _ExceptionT], Response]
Guard = Callable[[ASGIConnection, BaseRouteHandler], SyncOrAsyncUnion[None]]
LifeSpanHandler = Union[Callable[[], SyncOrAsyncUnion[Any]], Callable[[State], SyncOrAsyncUnion[Any]]]
LifeSpanHookHandler = Callable[[StarliteType], SyncOrAsyncUnion[None]]
OnAppInitHandler = Callable[[AppConfig], AppConfig]
Serializer = Callable[[Any], Any]
GetLogger = Callable[..., Logger]
