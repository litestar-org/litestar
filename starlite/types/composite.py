from typing import TYPE_CHECKING, Any, Callable, Dict, List, Type, Union

from .asgi_types import ASGIApp
from .callable_types import ExceptionHandler

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo  # noqa: TC004
    from starlette.middleware import Middleware as StarletteMiddleware  # noqa: TC004
    from starlette.middleware.base import BaseHTTPMiddleware  # noqa: TC004

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
    StarletteMiddleware = Any


Dependencies = Dict[str, Provide]
ExceptionHandlersMap = Dict[Union[int, Type[Exception]], ExceptionHandler]

Middleware = Union[
    Callable[..., ASGIApp], DefineMiddleware, StarletteMiddleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]
]
ParametersMap = Dict[str, FieldInfo]
ResponseCookies = List[Cookie]
ResponseHeadersMap = Dict[str, ResponseHeader]
