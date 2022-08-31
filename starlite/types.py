from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    MutableMapping,
    Type,
    TypeVar,
    Union,
)

from pydantic.fields import FieldInfo
from pydantic.typing import AnyCallable
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response as StarletteResponse
from typing_extensions import Literal

from starlite.exceptions import HTTPException

if TYPE_CHECKING:
    from starlette.middleware import Middleware as StarletteMiddleware  # noqa: TC004
    from starlette.middleware.base import BaseHTTPMiddleware  # noqa: TC004

    from starlite.app import Starlite  # noqa: TC004
    from starlite.connection import Request, WebSocket  # noqa: TC004
    from starlite.controller import Controller  # noqa: TC004
    from starlite.datastructures import Cookie, ResponseHeader, State  # noqa: TC004
    from starlite.handlers import BaseRouteHandler  # noqa: TC004
    from starlite.handlers.http import HTTPRouteHandler  # noqa: TC004
    from starlite.handlers.websocket import WebsocketRouteHandler  # noqa: TC004
    from starlite.middleware.base import (  # noqa: TC004
        DefineMiddleware,
        MiddlewareProtocol,
    )
    from starlite.provide import Provide  # noqa: TC004
    from starlite.response import Response  # noqa: TC004
    from starlite.router import Router  # noqa: TC004
else:
    BaseHTTPMiddleware = Any
    BaseRouteHandler = Any
    Controller = Any
    Cookie = Any
    DefineMiddleware = Any
    HTTPRouteHandler = Any
    MiddlewareProtocol = Any
    Provide = Any
    Request = Any
    Response = Any
    ResponseHeader = Any
    Router = Any
    StarletteMiddleware = Any
    Starlite = Any
    State = Any
    WebSocket = Any
    WebsocketRouteHandler = Any

# ASGI types - ported from 'starlette.types'
Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class Empty:
    """A sentinel class used as placeholder."""


EmptyType = Type[Empty]

T = TypeVar("T")
SyncOrAsyncUnion = Union[T, Awaitable[T]]
SingleOrList = Union[T, List[T]]

AfterExceptionHookHandler = Callable[[Exception, Scope, State], SyncOrAsyncUnion[None]]
AfterRequestHookHandler = Union[
    Callable[[StarletteResponse], SyncOrAsyncUnion[StarletteResponse]], Callable[[Response], SyncOrAsyncUnion[Response]]
]
AfterResponseHookHandler = Callable[[Request], Union[None, Awaitable[None]]]  # noqa: SIM907
AsyncAnyCallable = Callable[..., Awaitable[Any]]
BeforeMessageSendHookHandler = Callable[[Message, State], SyncOrAsyncUnion[None]]
BeforeRequestHookHandler = Callable[[Request], Union[Any, Awaitable[Any]]]
CacheKeyBuilder = Callable[[Request], str]
ControllerRouterHandler = Union[Type[Controller], BaseRouteHandler, Router, AnyCallable]
Dependencies = Dict[str, Provide]
ExceptionHandler = Callable[[Request, Union[Exception, HTTPException, StarletteHTTPException]], StarletteResponse]
ExceptionHandlersMap = Dict[Union[int, Type[Exception]], ExceptionHandler]
Guard = Union[
    Callable[[Request, HTTPRouteHandler], SyncOrAsyncUnion[None]],
    Callable[[WebSocket, WebsocketRouteHandler], SyncOrAsyncUnion[None]],
]
LifeSpanHandler = Union[Callable[[], SyncOrAsyncUnion[Any]], Callable[[State], SyncOrAsyncUnion[Any]]]
LifeSpanHookHandler = Callable[[Starlite], SyncOrAsyncUnion[None]]
Method = Literal["GET", "POST", "DELETE", "PATCH", "PUT", "HEAD"]
Middleware = Union[
    Callable[..., ASGIApp], DefineMiddleware, StarletteMiddleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]
]
ParametersMap = Dict[str, FieldInfo]
ReservedKwargs = Literal["request", "socket", "headers", "query", "cookies", "state", "data"]
ResponseCookies = List[Cookie]
ResponseHeadersMap = Dict[str, ResponseHeader]
ResponseType = Type[Response]


__all__ = [
    "ASGIApp",
    "AfterExceptionHookHandler",
    "AfterRequestHookHandler",
    "AfterResponseHookHandler",
    "AsyncAnyCallable",
    "BeforeMessageSendHookHandler",
    "BeforeRequestHookHandler",
    "CacheKeyBuilder",
    "ControllerRouterHandler",
    "Dependencies",
    "Empty",
    "EmptyType",
    "ExceptionHandler",
    "ExceptionHandlersMap",
    "Guard",
    "LifeSpanHandler",
    "LifeSpanHookHandler",
    "Message",
    "Method",
    "Middleware",
    "ParametersMap",
    "Receive",
    "ReservedKwargs",
    "ResponseCookies",
    "ResponseHeadersMap",
    "ResponseType",
    "Scope",
    "Send",
    "SyncOrAsyncUnion",
    "SingleOrList",
]
