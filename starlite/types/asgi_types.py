from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    MutableMapping,
    Optional,
    Tuple,
    Union,
)

from typing_extensions import Literal, TypedDict

from starlite.enums import ScopeType

if TYPE_CHECKING:
    from pydantic import BaseModel

    from starlite.app import Starlite

    from .empty import EmptyType
    from .internal_types import RouteHandlerType

Method = Literal["GET", "POST", "DELETE", "PATCH", "PUT", "HEAD", "TRACE", "OPTIONS"]


class ASGIVersion(TypedDict):
    spec_version: str
    version: Literal["3.0"]


class BaseScope(TypedDict):
    app: "Starlite"
    asgi: ASGIVersion
    auth: Any
    client: Optional[Tuple[str, int]]
    extensions: Optional[Dict[str, Dict[object, object]]]
    headers: Iterable[Tuple[bytes, bytes]]
    http_version: str
    path: str
    path_params: Dict[str, str]
    query_string: bytes
    raw_path: bytes
    root_path: str
    route_handler: "RouteHandlerType"
    scheme: str
    server: Optional[Tuple[str, Optional[int]]]
    session: Optional[Union["EmptyType", Dict[str, Any], "BaseModel"]]
    state: Dict[str, Any]
    user: Any


class HTTPScope(BaseScope):
    method: "Method"
    type: Literal[ScopeType.HTTP]


class WebSocketScope(BaseScope):
    subprotocols: Iterable[str]
    type: Literal[ScopeType.WEBSOCKET]


class LifeSpanScope(TypedDict):
    app: "Starlite"
    asgi: ASGIVersion
    type: Literal["lifespan"]


Scope = Union[HTTPScope, WebSocketScope]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
