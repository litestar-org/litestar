from contextlib import ExitStack
from queue import Queue
from typing import TYPE_CHECKING, Any, List, Literal, Optional, Tuple, Union, cast

from anyio import sleep

from starlite.exceptions import WebSocketDisconnect
from starlite.status_codes import WS_1000_NORMAL_CLOSURE
from starlite.utils.serialization import decode_json, encode_json

if TYPE_CHECKING:

    from starlite.testing.test_client.client import TestClient
    from starlite.types import (
        WebSocketConnectEvent,
        WebSocketDisconnectEvent,
        WebSocketReceiveMessage,
        WebSocketScope,
        WebSocketSendMessage,
    )


class WebSocketTestSession:
    exit_stack: "ExitStack"

    def __init__(
        self,
        client: "TestClient",
        scope: "WebSocketScope",
    ) -> None:
        self.client = client
        self.scope = scope
        self.accepted_subprotocol: Optional[str] = None
        self.receive_queue: "Queue[WebSocketReceiveMessage]" = Queue()
        self.send_queue: "Queue[Union[WebSocketSendMessage, BaseException]]" = Queue()
        self.extra_headers: Optional[List[Tuple[bytes, bytes]]] = None

    def __enter__(self) -> "WebSocketTestSession":
        self.exit_stack = ExitStack()

        portal = self.exit_stack.enter_context(self.client.portal())

        try:
            portal.start_task_soon(self.do_asgi_call)
            event: "WebSocketConnectEvent" = {"type": "websocket.connect"}
            self.receive_queue.put(event)

            message = self.receive()
            self.accepted_subprotocol = cast("Optional[str]", message.get("subprotocol", None))
            self.extra_headers = cast("Optional[List[Tuple[bytes, bytes]]]", message.get("headers", None))
            return self
        except Exception:
            self.exit_stack.close()
            raise

    def __exit__(self, *args: Any) -> None:
        try:
            self.close()
        finally:
            self.exit_stack.close()
        while not self.send_queue.empty():
            message = self.send_queue.get()
            if isinstance(message, BaseException):
                raise message

    async def do_asgi_call(self) -> None:
        """The sub-thread in which the websocket session runs."""

        async def receive() -> "WebSocketReceiveMessage":
            while self.receive_queue.empty():
                await sleep(0)
            return self.receive_queue.get()

        async def send(message: "WebSocketSendMessage") -> None:
            if message["type"] == "websocket.accept":
                headers = message.get("headers", [])
                if headers:
                    headers_list = list(self.scope["headers"])
                    headers_list.extend(headers)
                    self.scope["headers"] = headers_list
                subprotocols = cast("Optional[str]", message.get("subprotocols"))
                if subprotocols:
                    self.scope["subprotocols"].append(subprotocols)
            self.send_queue.put(message)

        try:
            await self.client.app(self.scope, receive, send)
        except BaseException as exc:
            self.send_queue.put(exc)
            raise

    def send(self, data: Union[str, bytes], mode: Literal["text", "binary"] = "text", encoding: str = "utf-8") -> None:
        """Sends a "receive" event. This is the inverse of the ASGI send method.

        Args:
            data: Either a string or a byte string.
            mode: The key to use - 'text' or 'bytes'
            encoding: The encoding to use when encoding or decoding data.

        Returns:
            None.
        """
        if mode == "text":
            data = data.decode(encoding) if isinstance(data, bytes) else data
            text_event: "WebSocketReceiveMessage" = {"type": "websocket.receive", "text": data}  # type: ignore[assignment]
            self.receive_queue.put(text_event)
        else:
            data = data if isinstance(data, bytes) else data.encode(encoding)
            binary_event: "WebSocketReceiveMessage" = {"type": "websocket.receive", "bytes": data}  # type: ignore[assignment]
            self.receive_queue.put(binary_event)

    def send_text(self, data: str, encoding: str = "utf-8") -> None:
        """Sends the data using the 'text' key.

        Args:
            data: Data to send.
            encoding: Encoding to use.

        Returns:
            None
        """
        self.send(data=data, encoding=encoding)

    def send_bytes(self, data: bytes, encoding: str = "utf-8") -> None:
        """Sends the data using the 'bytes' key.

        Args:
            data: Data to send.
            encoding: Encoding to use.

        Returns:
            None
        """
        self.send(data=data, mode="binary", encoding=encoding)

    def send_json(self, data: Any, mode: Literal["text", "binary"] = "text") -> None:
        """Sends the given data as JSON.

        Args:
            data: The data to send.
            mode: Either 'text' or 'binary'

        Returns:
            None.
        """
        self.send(encode_json(data), mode=mode)

    def close(self, code: int = WS_1000_NORMAL_CLOSURE) -> None:
        """Sends an 'websocket.disconnect' event.

        Args:
            code: status code for closing the connection.

        Returns:
            None.
        """
        event: "WebSocketDisconnectEvent" = {"type": "websocket.disconnect", "code": code}
        self.receive_queue.put(event)

    def receive(self) -> "WebSocketSendMessage":
        """This is the base receive method.

        Notes:
            - you can use one of the other receive methods to extract the data from the message.
        Returns:
            A websocket message.
        """
        message = cast("WebSocketSendMessage", self.send_queue.get())
        if isinstance(message, BaseException):
            raise message
        if message["type"] == "websocket.close":
            raise WebSocketDisconnect(
                detail=cast("str", message.get("reason", "")),
                code=message.get("code", WS_1000_NORMAL_CLOSURE),
            )
        return message

    def receive_text(self) -> str:
        """

        Returns:
            A string value.
        """
        message = self.receive()
        return cast("str", message.get("text", ""))

    def receive_bytes(self) -> bytes:
        """
        Returns:
            A bytes string value.
        """
        message = self.receive()
        return cast("bytes", message.get("bytes", b""))

    def receive_json(self, mode: Literal["text", "binary"] = "text") -> Any:
        """Receives JSON.

        Args:
            mode: Either 'text' or 'binary'

        Returns:
            An arbitrary value
        """
        message = self.receive()

        if mode == "text":
            return decode_json(cast("str", message.get("text", "")))

        return decode_json(cast("bytes", message.get("bytes", b"")))
