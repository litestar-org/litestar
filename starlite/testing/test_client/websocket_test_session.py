from contextlib import ExitStack
from queue import Queue
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union, cast

from anyio import sleep
from anyio.from_thread import start_blocking_portal
from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps, loads
from typing_extensions import Literal

from starlite.exceptions import WebSocketDisconnect
from starlite.status_codes import WS_1000_NORMAL_CLOSURE
from starlite.utils import default_serializer

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
        portal = self.exit_stack.enter_context(
            start_blocking_portal(backend=self.client.backend, backend_options=self.client.backend_options)
        )

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
            self.close(WS_1000_NORMAL_CLOSURE)
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
                    self.scope["headers"].extend(headers)
                subprotocols = cast("Optional[str]", message.get("subprotocols"))
                if subprotocols:
                    self.scope["subprotocols"].append(subprotocols)
            self.send_queue.put(message)

        try:
            await self.client.app(self.scope, receive, send)
        except BaseException as exc:
            self.send_queue.put(exc)
            raise

    def send(
        self, data: Union[str, bytes], mode: "Literal['text', 'binary']" = "text", encoding: str = "utf-8"
    ) -> None:
        """The 'send' here is the inverse of the ASGI 'send',

        that is - it receives 'eceive' events rather than 'send' events.
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
        self.send(data=data, mode="text", encoding=encoding)

    def send_bytes(self, data: bytes, encoding: str = "utf-8") -> None:
        self.send(data=data, mode="binary", encoding=encoding)

    def send_json(self, data: Any, mode: "Literal['text', 'binary']" = "text") -> None:
        self.send(
            data=dumps(data, default=default_serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS), mode=mode
        )

    def close(self, code: int = 1000) -> None:
        event: "WebSocketDisconnectEvent" = {"type": "websocket.disconnect", "code": code}
        self.receive_queue.put(event)

    def receive(self) -> "WebSocketSendMessage":
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
        message = self.receive()
        return cast("str", message.get("text", ""))

    def receive_bytes(self) -> bytes:
        message = self.receive()
        return cast("bytes", message.get("bytes", b""))

    def receive_json(self, mode: "Literal['text', 'binary']" = "text") -> Any:
        message = self.receive()
        if mode == "text":
            return loads(cast("str", message.get("text", "")))
        return loads(cast("bytes", message.get("bytes", b"")))
