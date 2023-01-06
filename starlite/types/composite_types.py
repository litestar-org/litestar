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

    from pydantic.fields import FieldInfo  # noqa: TC004

    from starlite.datastructures.cookie import Cookie  # noqa: TC004
    from starlite.datastructures.provide import Provide  # noqa: TC004
    from starlite.datastructures.response_header import ResponseHeader  # noqa: TC004
    from starlite.middleware.base import (  # noqa: TC004
        DefineMiddleware,
        MiddlewareProtocol,
    )
else:
    BaseHTTPMiddleware = Any
    Cookie = Any
    DefineMiddleware = Any
    FieldInfo = Any
    MiddlewareProtocol = Any
    Provide = Any
    ResponseHeader = Any

T = TypeVar("T")


Dependencies = Dict[str, Provide]
ExceptionHandlersMap = Dict[Union[int, Type[Exception]], ExceptionHandler]
ParametersMap = Dict[str, FieldInfo]
ResponseCookies = List[Cookie]
ResponseHeadersMap = Dict[str, ResponseHeader]
StreamType = Union[Iterable[T], Iterator[T], AsyncIterable[T], AsyncIterator[T]]
PathType = Union[Path, PathLike, str]
Scopes = Set[Literal[ScopeType.HTTP, ScopeType.WEBSOCKET]]
Middleware = Union[
    Callable[..., ASGIApp], DefineMiddleware, Iterator[Tuple[ASGIApp, Dict[str, Any]]], Type[MiddlewareProtocol]
]
MaybePartial = Union[T, partial]
TypeEncodersMap = Dict[Any, Callable[[Any], Any]]
