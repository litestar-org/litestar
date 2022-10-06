from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Union,
    cast,
    overload,
)

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps, loads
from starlette.datastructures import Headers
from starlette.status import WS_1000_NORMAL_CLOSURE

from starlite.connection.base import (
    ASGIConnection,
    Auth,
    User,
    empty_receive,
    empty_send,
)
from starlite.exceptions import WebSocketException
from starlite.utils.serialization import default_serializer

if TYPE_CHECKING:

    from typing_extensions import Literal

    from starlite.handlers.websocket import WebsocketRouteHandler  # noqa: F401
    from starlite.types import Message, Serializer, WebSocketScope
    from starlite.types.asgi_types import WebSocketDisconnectEvent  # nopycln: import
    from starlite.types.asgi_types import WebSocketReceiveEvent  # nopycln: import
    from starlite.types.asgi_types import (
        Receive,
        ReceiveMessage,
        Scope,
        Send,
        WebSocketAcceptEvent,
        WebSocketCloseEvent,
        WebSocketSendEvent,
    )

DISCONNECT_MESSAGE = "connection is disconnected"


class WebSocket(
    Generic[User, Auth],
    ASGIConnection["WebsocketRouteHandler", User, Auth],
):
    __slots__ = ("connection_state",)

    scope: "WebSocketScope"
    """
    The ASGI scope attached to the connection.
    """
    receive: "Receive"
    """
    The ASGI receive function.
    """
    send: "Send"
    """
    The ASGI send function.
    """

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send) -> None:
        """The Starlite WebSocket class.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        super().__init__(scope, self.receive_wrapper(receive), self.send_wrapper(send))
        self.connection_state: "Literal['init', 'connect', 'receive', 'disconnect']" = "init"

    def receive_wrapper(self, receive: "Receive") -> "Receive":
        """Wraps 'receive' to set 'self.connection_state' and validate events.

        Args:
            receive: The ASGI receive function.

        Returns:
            An ASGI receive function.
        """

        async def wrapped_receive() -> "ReceiveMessage":
            if self.connection_state == "disconnect":
                raise WebSocketException(detail=DISCONNECT_MESSAGE)
            message = await receive()
            if message["type"] == "websocket.connect":
                self.connection_state = "connect"
            elif message["type"] == "websocket.receive":
                self.connection_state = "receive"
            else:
                self.connection_state = "disconnect"
            return message

        return wrapped_receive

    def send_wrapper(self, send: "Send") -> "Send":
        """Wraps 'send' to ensure that state is not disconnected.

        Args:
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """

        async def wrapped_send(message: "Message") -> None:
            if self.connection_state == "disconnect":
                raise WebSocketException(detail=DISCONNECT_MESSAGE)  # pragma: no cover
            await send(message)

        return wrapped_send

    async def accept(
        self,
        subprotocols: Optional[str] = None,
        headers: Optional[Union[Headers, Dict[str, Any], List[Tuple[bytes, bytes]]]] = None,
    ) -> None:
        """Accepts the incoming connection. This method should be called before
        receiving data.

        Args:
            subprotocols: Websocket sub-protocol to use.
            headers: Headers to set on the data sent.

        Returns:
            None
        """
        if self.connection_state == "init":
            await self.receive()
            _headers: List[Tuple[bytes, bytes]] = headers if isinstance(headers, list) else []

            if isinstance(headers, dict):
                _headers = Headers(headers=headers).raw

            if isinstance(headers, Headers):
                _headers = headers.raw

            event: "WebSocketAcceptEvent" = {
                "type": "websocket.accept",
                "subprotocol": subprotocols,
                "headers": _headers,
            }
            await self.send(event)

    async def close(self, code: int = WS_1000_NORMAL_CLOSURE, reason: Optional[str] = None) -> None:
        """
        Sends an 'websocket.close' event.
        Args:
            code: Status code.
            reason: Reason for closing the connection

        Returns:
            None
        """
        event: "WebSocketCloseEvent" = {"type": "websocket.close", "code": code, "reason": reason or ""}
        await self.send(event)

    @overload
    async def receive_data(self, mode: "Literal['text']") -> str:
        """Overload of receive_data.

        Args:
            mode: Literal value 'text'

        Returns:
            A string.
        """

    @overload
    async def receive_data(self, mode: "Literal['binary']") -> bytes:
        """Overload of receive_data.

        Args:
            mode: Literal value 'binary'

        Returns:
            A byte-string.
        """

    async def receive_data(self, mode: "Literal['binary', 'text']") -> Union[str, bytes]:
        """Receive an 'websocket.receive' event and returns the data stored on
        it.

        Args:
            mode: The respective event key to use.

        Returns:
            The event's data.
        """
        if self.connection_state == "init":
            await self.accept()
        event = cast("Union['WebSocketReceiveEvent', 'WebSocketDisconnectEvent']", await self.receive())
        if event["type"] == "websocket.disconnect":
            raise WebSocketException(detail="disconnect event", code=event["code"])
        if self.connection_state == "disconnect":
            raise WebSocketException(detail=DISCONNECT_MESSAGE)
        return event.get("text") or "" if mode == "text" else event.get("bytes") or b""

    async def receive_text(self) -> str:
        """Receives data as text.

        Returns:
            A string.
        """
        return await self.receive_data(mode="text")

    async def receive_bytes(self) -> bytes:
        """Receives data as bytes.

        Returns:
            A byte-string.
        """
        return await self.receive_data(mode="binary")

    async def receive_json(
        self,
        mode: "Literal['text', 'binary']" = "text",
    ) -> Any:
        """Receives data and loads it into JSON using orson.

        Args:
            mode: Either 'text' or 'binary'.

        Returns:
            An arbitrary value
        """
        data = await self.receive_data(mode=mode)
        return loads(data)

    async def send_data(
        self, data: Union[str, bytes], mode: "Literal['text', 'binary']" = "text", encoding: str = "utf-8"
    ) -> None:
        """Sends a 'websocket.send' event.

        Args:
            data: Data to send.
            mode: The respective event key to use.
            encoding: Encoding to use when converting bytes / str.

        Returns:
            None
        """
        if self.connection_state == "init":
            await self.accept()
        event: "WebSocketSendEvent" = {"type": "websocket.send", "bytes": None, "text": None}
        if mode == "binary":
            event["bytes"] = data if isinstance(data, bytes) else data.encode(encoding)
        else:
            event["text"] = data if isinstance(data, str) else data.decode(encoding)
        await self.send(event)

    @overload
    async def send_text(self, data: bytes, encoding: str = "utf-8") -> None:
        ...

    @overload
    async def send_text(self, data: str) -> None:
        ...

    async def send_text(self, data: Union[str, bytes], encoding: str = "utf-8") -> None:
        """Sends data using the 'text' key of the send event.

        Args:
            data: Data to send
            encoding: Encoding to use for binary data.

        Returns:
            None
        """
        await self.send_data(data=data, mode="text", encoding=encoding)

    @overload
    async def send_bytes(self, data: bytes) -> None:
        ...

    @overload
    async def send_bytes(self, data: str, encoding: str = "utf-8") -> None:
        ...

    async def send_bytes(self, data: Union[str, bytes], encoding: str = "utf-8") -> None:
        """Sends data using the 'bytes' key of the send event.

        Args:
            data: Data to send
            encoding: Encoding to use for binary data.

        Returns:
            None
        """
        await self.send_data(data=data, mode="binary", encoding=encoding)

    async def send_json(
        self,
        data: Any,
        mode: "Literal['text', 'binary']" = "text",
        encoding: str = "utf-8",
        serializer: "Serializer" = default_serializer,
    ) -> None:
        """Sends data as JSON.

        Args:
            data: A value to serialize.
            mode: Either 'text' or 'binary'.
            encoding: Encoding to use for binary data.
            serializer: A serializer function.
        Returns:
            None
        """
        await self.send_data(
            data=dumps(data, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS),
            mode=mode,
            encoding=encoding,
        )
