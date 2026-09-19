from collections.abc import Callable, Mapping, MutableMapping, Sequence
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Union

from typing_extensions import TypeAliasType

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
    from litestar.datastructures.cookie import Cookie
    from litestar.datastructures.response_header import ResponseHeader
    from litestar.di import Provide
    from litestar.enums import ScopeType
    from litestar.params import ParameterKwarg

    from .asgi_types import ASGIApp
    from .callable_types import AnyCallable, ExceptionHandler

Dependencies = TypeAliasType("Dependencies", "Mapping[str, Union[Provide, AnyCallable]]")
ExceptionHandlersMap = TypeAliasType(
    "ExceptionHandlersMap", "MutableMapping[Union[int, type[Exception]], ExceptionHandler]"
)
Middleware = TypeAliasType("Middleware", Callable[..., "ASGIApp"])
MiddlewareFactory = TypeAliasType("MiddlewareFactory", Callable[..., Middleware])
ParametersMap = TypeAliasType("ParametersMap", "Mapping[str, ParameterKwarg]")
PathType = TypeAliasType("PathType", Union[Path, PathLike, str])
ResponseCookies = TypeAliasType("ResponseCookies", "Union[Sequence[Cookie], Mapping[str, str]]")
ResponseHeaders = TypeAliasType("ResponseHeaders", "Union[Sequence[ResponseHeader], Mapping[str, str]]")
Scopes = TypeAliasType("Scopes", "set[Literal[ScopeType.HTTP, ScopeType.WEBSOCKET]]")
TypeDecodersSequence = TypeAliasType(
    "TypeDecodersSequence", Sequence[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]]
)
TypeEncodersMap = TypeAliasType("TypeEncodersMap", Mapping[Any, Callable[[Any], Any]])
