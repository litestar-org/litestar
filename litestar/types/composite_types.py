from functools import partial
from os import PathLike
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterable,
    AsyncIterator,
    Callable,
    Dict,
    Iterable,
    Iterator,
    Literal,
    Mapping,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from litestar.enums import ScopeType

from .asgi_types import ASGIApp
from .callable_types import ExceptionHandler

if TYPE_CHECKING:
    from litestar.datastructures.cookie import Cookie
    from litestar.datastructures.response_header import ResponseHeader
    from litestar.di import Provide
    from litestar.middleware.base import DefineMiddleware, MiddlewareProtocol
    from litestar.params import ParameterKwarg
else:
    BaseHTTPMiddleware = Any
    Cookie = Any
    DefineMiddleware = Any
    ImmutableState = Any
    MiddlewareProtocol = Any
    ParameterKwarg = Any
    Provide = Any
    ResponseHeader = Any

T = TypeVar("T")


Dependencies = Mapping[str, Provide]
ExceptionHandlersMap = Mapping[Union[int, Type[Exception]], ExceptionHandler]
MaybePartial = Union[T, partial]
Middleware = Union[
    Callable[..., ASGIApp], DefineMiddleware, Iterator[Tuple[ASGIApp, Dict[str, Any]]], Type[MiddlewareProtocol]
]
ParametersMap = Mapping[str, ParameterKwarg]
PathType = Union[Path, PathLike, str]
ResponseCookies = Union[Sequence[Cookie], Mapping[str, str]]
ResponseHeaders = Union[Sequence[ResponseHeader], Mapping[str, str]]
Scopes = Set[Literal[ScopeType.HTTP, ScopeType.WEBSOCKET]]
StreamType = Union[Iterable[T], Iterator[T], AsyncIterable[T], AsyncIterator[T]]
TypeEncodersMap = Mapping[Any, Callable[[Any], Any]]
