from concurrent.futures import Future
from contextlib import ExitStack
from queue import Queue
from typing import TYPE_CHECKING, Any, Callable, ContextManager

from anyio import sleep
from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps, loads

from starlite.exceptions import WebSocketDisconnect
from starlite.status_codes import WS_1000_NORMAL_CLOSURE
from starlite.utils import default_serializer

if TYPE_CHECKING:
    from anyio.from_thread import BlockingPortal

    from starlite.types import (
        ASGIApp,
        Message,
        Scope,
        WebSocketConnectEvent,
        WebSocketDisconnectEvent,
        WebSocketReceiveMessage,
        WebSocketSendMessage,
    )


class WebSocketTestSession:
    def __init__(
        self,
        app: "ASGIApp",
        scope: "Scope",
        portal_factory: Callable[[], ContextManager["BlockingPortal"]],
    ) -> None:
        self.app = app
        self.scope = scope
        self.accepted_subprotocol = None
        self.portal_factory = portal_factory
        self._receive_queue: "Queue[Any]" = Queue()
        self._send_queue: "Queue[Any]" = Queue()
        self.extra_headers = None

    def __enter__(self) -> "WebSocketTestSession":
        self.exit_stack = ExitStack()
        self.portal = self.exit_stack.enter_context(self.portal_factory())

        try:
            _: "Future[None]" = self.portal.start_task_soon(self._run)
            event: "WebSocketConnectEvent" = {"type": "websocket.connect"}
            self.send(event)
            message = self.receive()
            self._raise_on_close(message)
        except Exception:
            self.exit_stack.close()
            raise
        self.accepted_subprotocol = message.get("subprotocol", None)
        self.extra_headers = message.get("headers", None)
        return self

    def __exit__(self, *args: Any) -> None:
        try:
            self.close(1000)
        finally:
            self.exit_stack.close()
        while not self._send_queue.empty():
            message = self._send_queue.get()
            if isinstance(message, BaseException):
                raise message

    async def _run(self) -> None:
        """The sub-thread in which the websocket session runs."""
        scope = self.scope
        receive = self._asgi_receive
        send = self._asgi_send
        try:
            await self.app(scope, receive, send)
        except BaseException as exc:
            self._send_queue.put(exc)
            raise

    async def _asgi_receive(self) -> "Message":
        while self._receive_queue.empty():
            await sleep(0)
        return self._receive_queue.get()

    async def _asgi_send(self, message: "Message") -> None:
        self._send_queue.put(message)

    @staticmethod
    def _raise_on_close(message: "WebSocketSendMessage") -> None:
        if message["type"] == "websocket.close":
            raise WebSocketDisconnect(
                detail=message.get("detail", message.get("reason", "")),
                code=message.get("code", WS_1000_NORMAL_CLOSURE),
            )

    def send(self, message: "WebSocketReceiveMessage") -> None:
        """The 'send' here is the inverse of the ASGI 'send',

        that is - it receives 'eceive' events rather than 'send' events.
        """
        self._receive_queue.put(message)

    def send_text(self, data: str) -> None:
        self.send({"type": "websocket.receive", "text": data})

    def send_bytes(self, data: bytes) -> None:
        self.send({"type": "websocket.receive", "bytes": data})

    def send_json(self, data: Any, mode: str = "text") -> None:
        text = dumps(data, default=default_serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
        if mode == "text":
            self.send({"type": "websocket.receive", "text": text.decode("utf-8")})
        else:
            self.send({"type": "websocket.receive", "bytes": text})

    def close(self, code: int = 1000) -> None:
        event: "WebSocketDisconnectEvent" = {"type": "websocket.disconnect", "code": code}
        self.send(event)

    def receive(self) -> "WebSocketSendMessage":
        message = self._send_queue.get()
        if isinstance(message, BaseException):
            raise message
        return message

    def receive_text(self) -> str:
        message = self.receive()
        self._raise_on_close(message)
        return message.get("text", "")

    def receive_bytes(self) -> bytes:
        message = self.receive()
        self._raise_on_close(message)
        return message.get("bytes", b"")

    def receive_json(self, mode: str = "text") -> Any:
        message = self.receive()
        self._raise_on_close(message)
        if mode == "text":
            return loads(message.get("text", ""))
        return loads(message.get("bytes", b""))
