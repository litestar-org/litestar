from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    Literal,
    Mapping,
    MutableMapping,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from litestar.enums import ScopeType

from .callable_types import AnyCallable, ExceptionHandler

__all__ = (
    "Dependencies",
    "ExceptionHandlersMap",
    "Middleware",
    "ParametersMap",
    "PathType",
    "ResponseCookies",
    "ResponseHeaders",
    "Scopes",
    "TypeEncodersMap",
)

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from litestar.datastructures.cookie import Cookie
    from litestar.datastructures.response_header import ResponseHeader
    from litestar.di import Provide
    from litestar.middleware.base import DefineMiddleware, MiddlewareProtocol
    from litestar.params import ParameterKwarg

    from .asgi_types import ASGIApp

    Dependencies: TypeAlias = Mapping[str, Union[Provide, AnyCallable]]
    Middleware: TypeAlias = Union[
        Callable[..., ASGIApp], DefineMiddleware, Iterator[Tuple[ASGIApp, Dict[str, Any]]], Type[MiddlewareProtocol]
    ]
    ParametersMap: TypeAlias = Mapping[str, ParameterKwarg]
    ResponseCookies: TypeAlias = Union[Sequence[Cookie], Mapping[str, str]]
    ResponseHeaders: TypeAlias = Union[Sequence[ResponseHeader], Mapping[str, str]]
else:
    Dependencies: TypeAlias = Any
    Middleware: TypeAlias = Any
    ParametersMap: TypeAlias = Any
    ResponseCookies: TypeAlias = Any
    ResponseHeaders: TypeAlias = Any

ExceptionHandlersMap: TypeAlias = MutableMapping[Union[int, Type[Exception]], ExceptionHandler]
PathType: TypeAlias = Union[Path, PathLike, str]
Scopes: TypeAlias = Set[Literal[ScopeType.HTTP, ScopeType.WEBSOCKET]]
TypeEncodersMap: TypeAlias = Mapping[Any, Callable[[Any], Any]]
