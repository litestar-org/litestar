from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Type,
    TypeVar,
    Union,
)

from pydantic.fields import FieldInfo
from pydantic.typing import AnyCallable
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import HTTPConnection
from starlette.responses import Response as StarletteResponse
from typing_extensions import Literal

from starlite.exceptions import HTTPException

if TYPE_CHECKING:

    from starlette.middleware import Middleware as StarletteMiddleware  # noqa: TC004
    from starlette.middleware.base import BaseHTTPMiddleware  # noqa: TC004
    from starlette.types import ASGIApp  # noqa: TC004

    from starlite.connection import Request  # noqa: TC004
    from starlite.controller import Controller  # noqa: TC004
    from starlite.datastructures import Cookie, ResponseHeader, State  # noqa: TC004
    from starlite.handlers import BaseRouteHandler  # noqa: TC004
    from starlite.middleware.base import (  # noqa: TC004
        DefineMiddleware,
        MiddlewareProtocol,
    )
    from starlite.provide import Provide  # noqa: TC004
    from starlite.response import Response  # noqa: TC004
    from starlite.router import Router  # noqa: TC004
else:
    ASGIApp = Any
    Request = Any
    WebSocket = Any
    BaseRouteHandler = Any
    Controller = Any
    Router = Any
    State = Any
    Response = Any
    MiddlewareProtocol = Any
    StarletteMiddleware = Any
    BaseHTTPMiddleware = Any
    DefineMiddleware = Any
    Provide = Any
    ResponseHeader = Any
    Cookie = Any

H = TypeVar("H", bound=HTTPConnection)

Middleware = Union[
    StarletteMiddleware, DefineMiddleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol], Callable[..., ASGIApp]
]
ResponseType = Type[Response]
ExceptionHandler = Callable[
    [Request, Union[Exception, HTTPException, StarletteHTTPException]], Union[Response, StarletteResponse]
]
ExceptionHandlersMap = Dict[Union[int, Type[Exception]], ExceptionHandler]
LifeCycleHandler = Union[
    Callable[[], Any],
    Callable[[State], Any],
    Callable[[], Awaitable[Any]],
    Callable[[State], Awaitable[Any]],
]
Guard = Union[Callable[[H, BaseRouteHandler], Awaitable[None]], Callable[[H, BaseRouteHandler], None]]
Method = Literal["GET", "POST", "DELETE", "PATCH", "PUT", "HEAD"]
ReservedKwargs = Literal["request", "socket", "headers", "query", "cookies", "state", "data"]
ControllerRouterHandler = Union[Type[Controller], BaseRouteHandler, Router, AnyCallable]
Dependencies = Dict[str, Provide]
ParametersMap = Dict[str, FieldInfo]
ResponseHeadersMap = Dict[str, ResponseHeader]
ResponseCookies = List[Cookie]
# connection-lifecycle hook handlers
BeforeRequestHandler = Union[Callable[[Request], Any], Callable[[Request], Awaitable[Any]]]
AfterRequestHandler = Union[
    Callable[[Response], Response],
    Callable[[Response], Awaitable[Response]],
    Callable[[StarletteResponse], StarletteResponse],
    Callable[[StarletteResponse], Awaitable[StarletteResponse]],
]
AfterResponseHandler = Union[Callable[[Request], None], Callable[[Request], Awaitable[None]]]

AsyncAnyCallable = Callable[..., Awaitable[Any]]
CacheKeyBuilder = Callable[[Request], str]


class Empty:
    """A sentinel class used as placeholder."""


EmptyType = Type[Empty]
