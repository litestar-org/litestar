from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)

from pydantic import BaseModel, create_model
from pydantic.typing import AnyCallable
from pydantic_openapi_schema.v3_1_0.header import Header
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import HTTPConnection
from starlette.responses import Response as StarletteResponse
from typing_extensions import Literal, Protocol, runtime_checkable

from starlite.exceptions import HTTPException, ImproperlyConfiguredException
from starlite.response import Response

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from starlite.connection import Request  # noqa: TC004
    from starlite.controller import Controller  # noqa: TC004
    from starlite.datastructures import State  # noqa: TC004
    from starlite.handlers import BaseRouteHandler  # noqa: TC004
    from starlite.router import Router  # noqa: TC004
else:
    Request = Any
    WebSocket = Any
    BaseRouteHandler = Any
    Controller = Any
    Router = Any
    State = Any

T = TypeVar("T", bound=BaseModel)
H = TypeVar("H", bound=HTTPConnection)

ExceptionHandler = Callable[
    [Request, Union[Exception, HTTPException, StarletteHTTPException]], Union[Response, StarletteResponse]
]
LifeCycleHandler = Union[
    Callable[[], Any],
    Callable[[State], Any],
    Callable[[], Awaitable[Any]],
    Callable[[State], Awaitable[Any]],
]
Guard = Union[Callable[[H, BaseRouteHandler], Awaitable[None]], Callable[[H, BaseRouteHandler], None]]
Method = Union[Literal["GET"], Literal["POST"], Literal["DELETE"], Literal["PATCH"], Literal["PUT"], Literal["HEAD"]]
ReservedKwargs = Union[
    Literal["request"],
    Literal["socket"],
    Literal["headers"],
    Literal["query"],
    Literal["cookies"],
    Literal["state"],
    Literal["data"],
]
ControllerRouterHandler = Union[Type[Controller], BaseRouteHandler, Router, AnyCallable]

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


@runtime_checkable
class MiddlewareProtocol(Protocol):
    def __init__(self, app: "ASGIApp"):  # pragma: no cover
        ...

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:  # pragma: no cover
        ...


class Partial(Generic[T]):
    _models: Dict[Type[T], Any] = {}

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        """
        Modifies a given T subclass of BaseModel to be all optional
        """
        if not issubclass(item, BaseModel):
            raise ImproperlyConfiguredException(f"Partial[{item}] must be a subclass of BaseModel")
        if not cls._models.get(item):
            field_definitions: Dict[str, Tuple[Any, None]] = {}
            # traverse the object's mro and get all annotations
            # until we find a BaseModel.
            for obj in item.mro():
                if issubclass(obj, BaseModel):
                    for field_name, field_type in get_type_hints(obj).items():
                        # we modify the field annotations to make it optional
                        if not isinstance(field_type, GenericAlias) or type(None) not in field_type.__args__:
                            field_definitions[field_name] = (Optional[field_type], None)
                        else:
                            field_definitions[field_name] = (field_type, None)
                else:
                    break
            cls._models[item] = create_model(f"Partial{item.__name__}", **field_definitions)  # type: ignore
        return cast("Type[T]", cls._models.get(item))


class ResponseHeader(Header):
    value: Any = ...


Middleware = Union[StarletteMiddleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]
