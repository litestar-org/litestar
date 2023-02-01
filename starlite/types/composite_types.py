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
    List,
    Literal,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from starlite.enums import ScopeType

from .asgi_types import ASGIApp
from .callable_types import ExceptionHandler

if TYPE_CHECKING:
    from starlite.datastructures.cookie import Cookie
    from starlite.datastructures.provide import Provide
    from starlite.datastructures.response_header import ResponseHeader
    from starlite.datastructures.state import ImmutableState
    from starlite.middleware.base import DefineMiddleware, MiddlewareProtocol
    from starlite.params import ParameterKwarg
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


Dependencies = Dict[str, Provide]
ExceptionHandlersMap = Dict[Union[int, Type[Exception]], ExceptionHandler]
InitialStateType = Union[ImmutableState, Dict[str, Any], Iterable[Tuple[str, Any]]]
MaybePartial = Union[T, partial]
Middleware = Union[
    Callable[..., ASGIApp], DefineMiddleware, Iterator[Tuple[ASGIApp, Dict[str, Any]]], Type[MiddlewareProtocol]
]
ParametersMap = Dict[str, ParameterKwarg]
PathType = Union[Path, PathLike, str]
ResponseCookies = List[Cookie]
ResponseHeadersMap = Dict[str, ResponseHeader]
Scopes = Set[Literal[ScopeType.HTTP, ScopeType.WEBSOCKET]]
StreamType = Union[Iterable[T], Iterator[T], AsyncIterable[T], AsyncIterator[T]]
TypeEncodersMap = Dict[Any, Callable[[Any], Any]]
