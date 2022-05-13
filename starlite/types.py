from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from openapi_schema_pydantic import Header
from pydantic import BaseModel, create_model
from pydantic.typing import AnyCallable
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import HTTPConnection
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from typing_extensions import Literal, Protocol, Type, runtime_checkable

from starlite.exceptions import HTTPException
from starlite.response import Response

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from starlite.connection import Request
    from starlite.controller import Controller
    from starlite.datastructures import State
    from starlite.handlers import BaseRouteHandler
    from starlite.router import Router
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

AsyncAnyCallable = Callable[..., Awaitable[Any]]
CacheKeyBuilder = Callable[[Request], str]


@runtime_checkable
class MiddlewareProtocol(Protocol):
    def __init__(self, app: ASGIApp):  # pragma: no cover
        ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:  # pragma: no cover
        ...


class Partial(Generic[T]):
    _models: Dict[Type[T], Any] = {}

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        """
        Modifies a given T subclass of BaseModel to be all optional
        """
        if not cls._models.get(item):
            field_definitions: Dict[str, Tuple[Any, None]] = {}
            for field_name, field_type in item.__annotations__.items():
                # we modify the field annotations to make it optional
                if not isinstance(field_type, GenericAlias) or type(None) not in field_type.__args__:
                    field_definitions[field_name] = (Optional[field_type], None)
                else:
                    field_definitions[field_name] = (field_type, None)
                cls._models[item] = create_model("Partial" + item.__name__, **field_definitions)  # type: ignore
        return cast(Type[T], cls._models.get(item))


class ResponseHeader(Header):  # type: ignore
    value: Any = ...
