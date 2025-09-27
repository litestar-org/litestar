from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Literal

__all__ = (
    "Dependencies",
    "ExceptionHandlersMap",
    "Middleware",
    "MiddlewareFactory",
    "ParametersMap",
    "PathType",
    "ResponseCookies",
    "ResponseHeaders",
    "Scopes",
    "TypeEncodersMap",
)


if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping, Sequence
    from os import PathLike
    from pathlib import Path

    from typing_extensions import TypeAlias

    from litestar.datastructures.cookie import Cookie
    from litestar.datastructures.response_header import ResponseHeader
    from litestar.di import Provide
    from litestar.enums import ScopeType
    from litestar.params import ParameterKwarg

    from .asgi_types import ASGIApp
    from .callable_types import AnyCallable, ExceptionHandler

Dependencies: TypeAlias = "Mapping[str, Provide | AnyCallable]"
ExceptionHandlersMap: TypeAlias = "MutableMapping[int | type[Exception], ExceptionHandler]"
Middleware: TypeAlias = Callable[..., "ASGIApp"]
MiddlewareFactory: TypeAlias = Callable[..., Middleware]
ParametersMap: TypeAlias = "Mapping[str, ParameterKwarg]"
PathType: TypeAlias = "Path | PathLike | str"
ResponseCookies: TypeAlias = "Sequence[Cookie] | Mapping[str, str]"
ResponseHeaders: TypeAlias = "Sequence[ResponseHeader] | Mapping[str, str]"
Scopes: TypeAlias = "set[Literal[ScopeType.HTTP, ScopeType.WEBSOCKET]]"
TypeDecodersSequence: TypeAlias = "Sequence[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]]"
TypeEncodersMap: TypeAlias = "Mapping[Any, Callable[[Any], Any]]"
