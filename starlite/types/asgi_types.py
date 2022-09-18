"""This file includes code adapted from
https://github.com/django/asgiref/blob/main/asgiref/typing.py.

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
    List,
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
    headers: List[Tuple[bytes, bytes]]
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
    subprotocols: List[str]
    type: Literal[ScopeType.WEBSOCKET]


class LifeSpanScope(TypedDict):
    app: "Starlite"
    asgi: ASGIVersion
    type: Literal["lifespan"]


class HTTPRequestEvent(TypedDict):
    type: Literal["http.request"]
    body: bytes
    more_body: bool


class HTTPResponseStartEvent(TypedDict):
    type: Literal["http.response.start"]
    status: int
    headers: List[Tuple[bytes, bytes]]


class HTTPResponseBodyEvent(TypedDict):
    type: Literal["http.response.body"]
    body: bytes
    more_body: bool


class HTTPServerPushEvent(TypedDict):
    type: Literal["http.response.push"]
    path: str
    headers: List[Tuple[bytes, bytes]]


class HTTPDisconnectEvent(TypedDict):
    type: Literal["http.disconnect"]


class WebSocketConnectEvent(TypedDict):
    type: Literal["websocket.connect"]


class WebSocketAcceptEvent(TypedDict):
    type: Literal["websocket.accept"]
    subprotocol: Optional[str]
    headers: List[Tuple[bytes, bytes]]


class WebSocketReceiveEvent(TypedDict):
    type: Literal["websocket.receive"]
    bytes: Optional[bytes]
    text: Optional[str]


class WebSocketSendEvent(TypedDict):
    type: Literal["websocket.send"]
    bytes: Optional[bytes]
    text: Optional[str]


class WebSocketResponseStartEvent(TypedDict):
    type: Literal["websocket.http.response.start"]
    status: int
    headers: List[Tuple[bytes, bytes]]


class WebSocketResponseBodyEvent(TypedDict):
    type: Literal["websocket.http.response.body"]
    body: bytes
    more_body: bool


class WebSocketDisconnectEvent(TypedDict):
    type: Literal["websocket.disconnect"]
    code: int


class WebSocketCloseEvent(TypedDict):
    type: Literal["websocket.close"]
    code: int
    reason: Optional[str]


class LifeSpanStartupEvent(TypedDict):
    type: Literal["lifespan.startup"]


class LifeSpanShutdownEvent(TypedDict):
    type: Literal["lifespan.shutdown"]


class LifeSpanStartupCompleteEvent(TypedDict):
    type: Literal["lifespan.startup.complete"]


class LifeSpanStartupFailedEvent(TypedDict):
    type: Literal["lifespan.startup.failed"]
    message: str


class LifeSpanShutdownCompleteEvent(TypedDict):
    type: Literal["lifespan.shutdown.complete"]


class LifeSpanShutdownFailedEvent(TypedDict):
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
