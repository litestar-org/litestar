"""Includes code adapted from https://github.com/django/asgiref/blob/main/asgiref/typing.py.

Copyright (c) Django Software Foundation and individual contributors.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    3. Neither the name of Django nor the names of its contributors may be used
       to endorse or promote products derived from this software without
       specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
)

from typing_extensions import TypedDict

from starlite.enums import ScopeType

if TYPE_CHECKING:
    from pydantic import BaseModel

    from starlite.app import Starlite

    from .empty import EmptyType
    from .internal_types import RouteHandlerType

Method = Literal["GET", "POST", "DELETE", "PATCH", "PUT", "HEAD", "TRACE", "OPTIONS"]
ScopeSession = Optional[Union["EmptyType", Dict[str, Any], "BaseModel"]]


class ASGIVersion(TypedDict):
    """ASGI spec version."""

    spec_version: str
    version: Literal["3.0"]


class HeaderScope(TypedDict):
    """Base class for ASGI-scopes that supports headers."""

    headers: "RawHeaders"


class BaseScope(HeaderScope):
    """Base ASGI-scope."""

    app: "Starlite"
    asgi: ASGIVersion
    auth: Any
    client: Optional[Tuple[str, int]]
    extensions: Optional[Dict[str, Dict[object, object]]]
    http_version: str
    path: str
    path_params: Dict[str, str]
    query_string: bytes
    raw_path: bytes
    root_path: str
    route_handler: "RouteHandlerType"
    scheme: str
    server: Optional[Tuple[str, Optional[int]]]
    session: ScopeSession
    state: Dict[str, Any]
    user: Any


class HTTPScope(BaseScope):
    """HTTP-ASGI-scope."""

    method: "Method"
    type: Literal[ScopeType.HTTP]


class WebSocketScope(BaseScope):
    """WebSocket-ASGI-scope."""

    subprotocols: List[str]
    type: Literal[ScopeType.WEBSOCKET]


class LifeSpanScope(TypedDict):
    """Lifespan-ASGI-scope."""

    app: "Starlite"
    asgi: ASGIVersion
    type: Literal["lifespan"]


class HTTPRequestEvent(TypedDict):
    """ASGI `http.request` event."""

    type: Literal["http.request"]
    body: bytes
    more_body: bool


class HTTPResponseStartEvent(HeaderScope):
    """ASGI `http.response.start` event."""

    type: Literal["http.response.start"]
    status: int


class HTTPResponseBodyEvent(TypedDict):
    """ASGI `http.response.body` event."""

    type: Literal["http.response.body"]
    body: bytes
    more_body: bool


class HTTPServerPushEvent(HeaderScope):
    """ASGI `http.response.push` event."""

    type: Literal["http.response.push"]
    path: str


class HTTPDisconnectEvent(TypedDict):
    """ASGI `http.disconnect` event."""

    type: Literal["http.disconnect"]


class WebSocketConnectEvent(TypedDict):
    """ASGI `websocket.connect` event."""

    type: Literal["websocket.connect"]


class WebSocketAcceptEvent(HeaderScope):
    """ASGI `websocket.accept` event."""

    type: Literal["websocket.accept"]
    subprotocol: Optional[str]


class WebSocketReceiveEvent(TypedDict):
    """ASGI `websocket.receive` event."""

    type: Literal["websocket.receive"]
    bytes: Optional[bytes]
    text: Optional[str]


class WebSocketSendEvent(TypedDict):
    """ASGI `websocket.send` event."""

    type: Literal["websocket.send"]
    bytes: Optional[bytes]
    text: Optional[str]


class WebSocketResponseStartEvent(HeaderScope):
    """ASGI `websocket.http.response.start` event."""

    type: Literal["websocket.http.response.start"]
    status: int


class WebSocketResponseBodyEvent(TypedDict):
    """ASGI `websocket.http.response.body` event."""

    type: Literal["websocket.http.response.body"]
    body: bytes
    more_body: bool


class WebSocketDisconnectEvent(TypedDict):
    """ASGI `websocket.disconnect` event."""

    type: Literal["websocket.disconnect"]
    code: int


class WebSocketCloseEvent(TypedDict):
    """ASGI `websocket.close` event."""

    type: Literal["websocket.close"]
    code: int
    reason: Optional[str]


class LifeSpanStartupEvent(TypedDict):
    """ASGI `lifespan.startup` event."""

    type: Literal["lifespan.startup"]


class LifeSpanShutdownEvent(TypedDict):
    """ASGI `lifespan.shutdown` event."""

    type: Literal["lifespan.shutdown"]


class LifeSpanStartupCompleteEvent(TypedDict):
    """ASGI `lifespan.startup.complete` event."""

    type: Literal["lifespan.startup.complete"]


class LifeSpanStartupFailedEvent(TypedDict):
    """ASGI `lifespan.startup.failed` event."""

    type: Literal["lifespan.startup.failed"]
    message: str


class LifeSpanShutdownCompleteEvent(TypedDict):
    """ASGI `lifespan.shutdown.complete` event."""

    type: Literal["lifespan.shutdown.complete"]


class LifeSpanShutdownFailedEvent(TypedDict):
    """ASGI `lifespan.shutdown.failed` event."""

    type: Literal["lifespan.shutdown.failed"]
    message: str


HTTPReceiveMessage = Union[
    HTTPRequestEvent,
    HTTPDisconnectEvent,
]
WebSocketReceiveMessage = Union[
    WebSocketConnectEvent,
    WebSocketReceiveEvent,
    WebSocketDisconnectEvent,
]
LifeSpanReceiveMessage = Union[
    LifeSpanStartupEvent,
    LifeSpanShutdownEvent,
]
HTTPSendMessage = Union[
    HTTPResponseStartEvent,
    HTTPResponseBodyEvent,
    HTTPServerPushEvent,
    HTTPDisconnectEvent,
]
WebSocketSendMessage = Union[
    WebSocketAcceptEvent,
    WebSocketSendEvent,
    WebSocketResponseStartEvent,
    WebSocketResponseBodyEvent,
    WebSocketCloseEvent,
]
LifeSpanSendMessage = Union[
    LifeSpanStartupCompleteEvent,
    LifeSpanStartupFailedEvent,
    LifeSpanShutdownCompleteEvent,
    LifeSpanShutdownFailedEvent,
]
LifeSpanReceive = Callable[..., Awaitable[LifeSpanReceiveMessage]]
LifeSpanSend = Callable[[LifeSpanSendMessage], Awaitable[None]]
Message = Union[HTTPSendMessage, WebSocketSendMessage]
ReceiveMessage = Union[HTTPReceiveMessage, WebSocketReceiveMessage]
Scope = Union[HTTPScope, WebSocketScope]
Receive = Callable[..., Awaitable[Union[HTTPReceiveMessage, WebSocketReceiveMessage]]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
RawHeaders = Iterable[Tuple[bytes, bytes]]
RawHeadersList = List[Tuple[bytes, bytes]]
