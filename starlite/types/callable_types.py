from typing import TYPE_CHECKING, Any, Awaitable, Callable, Union

from .asgi_types import Message, Scope
from .helpers import SyncOrAsyncUnion
from .internal_types import StarliteType

if TYPE_CHECKING:
    from starlette.responses import Response as StarletteResponse  # noqa: TC004

    from starlite.config import AppConfig  # noqa: TC004
    from starlite.connection import Request, WebSocket  # noqa: TC004
    from starlite.datastructures.state import State  # noqa: TC004
    from starlite.handlers import HTTPRouteHandler, WebsocketRouteHandler  # noqa: TC004
    from starlite.response import Response  # noqa: TC004
    from starlite.types.protocols import Logger  # noqa: TC004
else:
    AppConfig = Any
    HTTPRouteHandler = Any
    Request = Any
    Response = Any
    StarletteResponse = Any
    State = Any
    WebSocket = Any
    WebsocketRouteHandler = Any
    Logger = Any

AfterExceptionHookHandler = Callable[[Exception, Scope, State], SyncOrAsyncUnion[None]]
AfterRequestHookHandler = Union[
    Callable[[StarletteResponse], SyncOrAsyncUnion[StarletteResponse]], Callable[[Response], SyncOrAsyncUnion[Response]]
]
AfterResponseHookHandler = Callable[[Request], SyncOrAsyncUnion[None]]
AsyncAnyCallable = Callable[..., Awaitable[Any]]
AnyCallable = Callable[..., Any]
BeforeMessageSendHookHandler = Union[
    Callable[[Message, State, Scope], SyncOrAsyncUnion[None]], Callable[[Message, State], SyncOrAsyncUnion[None]]
]
BeforeRequestHookHandler = Callable[[Request], Union[Any, Awaitable[Any]]]
CacheKeyBuilder = Callable[[Request], str]
ExceptionHandler = Callable[[Request, Exception], StarletteResponse]
Guard = Union[
    Callable[[Request, HTTPRouteHandler], SyncOrAsyncUnion[None]],
    Callable[[WebSocket, WebsocketRouteHandler], SyncOrAsyncUnion[None]],
]
LifeSpanHandler = Union[Callable[[], SyncOrAsyncUnion[Any]], Callable[[State], SyncOrAsyncUnion[Any]]]
LifeSpanHookHandler = Callable[[StarliteType], SyncOrAsyncUnion[None]]
OnAppInitHandler = Callable[[AppConfig], AppConfig]
Serializer = Callable[[Any], Any]
GetLogger = Callable[..., Logger]
