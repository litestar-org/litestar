from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING, Any, Literal, cast

import anyio
import anyio.abc
from anyio.streams.stapled import StapledObjectStream

from litestar.exceptions import WebSocketDisconnect
from litestar.serialization import decode_json, decode_msgpack, encode_json, encode_msgpack
from litestar.status_codes import WS_1000_NORMAL_CLOSURE

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar import Litestar
    from litestar.testing.client.sync_client import TestClient
    from litestar.types import (
        WebSocketDisconnectEvent,
        WebSocketReceiveMessage,
        WebSocketScope,
        WebSocketSendMessage,
    )


__all__ = ("AsyncWebSocketTestSession", "WebSocketTestSession")


class WebSocketTestSession:
    def __init__(
        self,
        client: TestClient[Any],
        scope: WebSocketScope,
        portal: anyio.abc.BlockingPortal,
        connect_timeout: float | None = None,
    ) -> None:
        self._exit_stack = contextlib.ExitStack()
        self._portal = portal
        self._client = client
        self._scope = scope
        self._connect_timeout = connect_timeout

    @contextlib.asynccontextmanager
    async def _run_session(self) -> AsyncGenerator[AsyncWebSocketTestSession]:
        async with (
            anyio.create_task_group() as tg,
            AsyncWebSocketTestSession(
                app=self._client.app,
                scope=self._scope,
                connect_timeout=self._connect_timeout,
                tg=tg,
            ) as session,
        ):
            yield session

    def __enter__(self) -> WebSocketTestSession:
        with contextlib.ExitStack() as exit_stack:
            self._async_session = exit_stack.enter_context(
                self._portal.wrap_async_context_manager(self._portal.call(self._run_session))
            )

            self._exit_stack = exit_stack.pop_all()

            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._exit_stack.close()

    @property
    def accepted_subprotocol(self) -> str:
        return self._async_session.accepted_subprotocol

    @property
    def extra_headers(self) -> list[tuple[bytes, bytes]]:
        return self._async_session.extra_headers

    @property
    def scope(self) -> WebSocketScope:
        return self._async_session.scope

    def send(self, data: str | bytes, mode: Literal["text", "binary"] = "text", encoding: str = "utf-8") -> None:
        """Sends a "receive" event. This is the inverse of the ASGI send method.

        Args:
            data: Either a string or a byte string.
            mode: The key to use - ``text`` or ``bytes``
            encoding: The encoding to use when encoding or decoding data.

        Returns:
            None.
        """
        self._portal.call(self._async_session.send, data, mode, encoding)

    def send_text(self, data: str, encoding: str = "utf-8") -> None:
        """Sends the data using the ``text`` key.

        Args:
            data: Data to send.
            encoding: Encoding to use.

        Returns:
            None
        """
        self._portal.call(self._async_session.send_text, data, encoding)

    def send_bytes(self, data: bytes, encoding: str = "utf-8") -> None:
        """Sends the data using the ``bytes`` key.

        Args:
            data: Data to send.
            encoding: Encoding to use.

        Returns:
            None
        """
        self._portal.call(self._async_session.send_bytes, data, encoding)

    def send_json(self, data: Any, mode: Literal["text", "binary"] = "text") -> None:
        """Sends the given data as JSON.

        Args:
            data: The data to send.
            mode: Either ``text`` or ``binary``

        Returns:
            None
        """
        self.send(encode_json(data), mode=mode)

    def send_msgpack(self, data: Any) -> None:
        """Sends the given data as MessagePack.

        Args:
            data: The data to send.

        Returns:
            None
        """
        self.send(encode_msgpack(data), mode="binary")

    def close(self, code: int = WS_1000_NORMAL_CLOSURE, reason: str | None = None) -> None:
        """Sends an 'websocket.disconnect' event.

        Args:
            code: status code for closing the connection.
            reason: Reason for closure

        Returns:
            None.
        """
        self._portal.call(self._async_session.close, code, reason)

    def receive(self, block: bool = True, timeout: float | None = None) -> WebSocketSendMessage:
        """This is the base receive method.

        Args:
            block: Block until a message is received
            timeout: If ``block`` is ``True``, block at most ``timeout`` seconds

        Notes:
            - you can use one of the other receive methods to extract the data from the message.

        Returns:
            A websocket message.
        """
        return self._portal.call(self._async_session.receive, block, timeout)

    def receive_text(self, block: bool = True, timeout: float | None = None) -> str:
        """Receive data in ``text`` mode and return a string

        Args:
            block: Block until a message is received
            timeout: If ``block`` is ``True``, block at most ``timeout`` seconds

        Returns:
            A string value.
        """
        return self._portal.call(self._async_session.receive_text, block, timeout)

    def receive_bytes(self, block: bool = True, timeout: float | None = None) -> bytes:
        """Receive data in ``binary`` mode and return bytes

        Args:
            block: Block until a message is received
            timeout: If ``block`` is ``True``, block at most ``timeout`` seconds

        Returns:
            A string value.
        """
        return self._portal.call(self._async_session.receive_bytes, block, timeout)

    def receive_json(
        self, mode: Literal["text", "binary"] = "text", block: bool = True, timeout: float | None = None
    ) -> Any:
        """Receive data in either ``text`` or ``binary`` mode and decode it as JSON.

        Args:
            mode: Either ``text`` or ``binary``
            block: Block until a message is received
            timeout: If ``block`` is ``True``, block at most ``timeout`` seconds

        Returns:
            An arbitrary value
        """
        return self._portal.call(self._async_session.receive_json, mode, block, timeout)

    def receive_msgpack(self, block: bool = True, timeout: float | None = None) -> Any:
        return self._portal.call(self._async_session.receive_msgpack, block, timeout)


class AsyncWebSocketTestSession:
    def __init__(
        self,
        *,
        app: Litestar,
        scope: WebSocketScope,
        connect_timeout: float | None = None,
        tg: anyio.abc.TaskGroup,
    ) -> None:
        self.scope = scope
        self.accepted_subprotocol: str | None = None
        self.extra_headers: list[tuple[bytes, bytes]] = []
        self.app = app

        self._tg: anyio.TaskGroup = tg
        self._send_stream = StapledObjectStream(*anyio.create_memory_object_stream["WebSocketSendMessage"](math.inf))
        self._receive_stream = StapledObjectStream(*anyio.create_memory_object_stream["WebSocketSendMessage"](math.inf))
        self._exit_stack = contextlib.AsyncExitStack()
        self._connect_timeout = connect_timeout

    async def __aenter__(self) -> AsyncWebSocketTestSession:
        async with contextlib.AsyncExitStack() as exit_stack:
            cancel_scope = anyio.CancelScope()
            app_done = await self._tg.start(self._run, cancel_scope, self._receive_stream, self._send_stream)

            exit_stack.callback(cancel_scope.cancel)
            exit_stack.push_async_callback(app_done.wait)
            exit_stack.push_async_callback(self.close)

            await self._asgi_send({"type": "websocket.connect"})
            message = await self.receive(timeout=self._connect_timeout)
            await self._raise_on_close(message)
            self.accepted_subprotocol = message.get("subprotocol")
            self.extra_headers = message.get("headers")
            self._exit_stack = exit_stack.pop_all()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._exit_stack.__aexit__(*args)

    async def _run(
        self,
        cancel_scope: anyio.CancelScope,
        receive_stream: StapledObjectStream,
        send_stream: StapledObjectStream,
        *,
        task_status: anyio.abc.TaskStatus,
    ) -> None:
        app_done = anyio.Event()
        with cancel_scope:
            async with send_stream, receive_stream:
                task_status.started(app_done)
                await self.app(self.scope, receive_stream.receive, send_stream.send)
                app_done.set()
                await anyio.sleep_forever()

    async def _raise_on_close(self, message: WebSocketSendMessage) -> None:
        if message["type"] == "websocket.close":
            raise WebSocketDisconnect(code=message.get("code", 1000), reason=message.get("reason", ""))
        if message["type"] == "websocket.http.response.start":
            while True:
                await self.receive()
                if message["type"] != "websocket.http.response.body":
                    raise RuntimeError(
                        f"Unexpected ASGI message type. Got {message['type']!r}, expected 'websocket.http.response.body'"
                    )
                if not message.get("more_body", False):
                    break

            raise RuntimeError("Unexpected early closure of WebSocket session")

    async def _asgi_send(self, message) -> None:
        await self._receive_stream.send(message)

    async def _asgi_receive(self):
        return await self._send_stream.receive()

    async def close(self, code: int = WS_1000_NORMAL_CLOSURE, reason: str | None = None) -> None:
        """Sends an 'websocket.disconnect' event.

        Args:
            code: status code for closing the connection.
            reason: Reason for closure

        Returns:
            None.
        """
        event: WebSocketDisconnectEvent = {"type": "websocket.disconnect", "code": code, "reason": reason}
        await self._asgi_send(event)

    async def send(self, data: str | bytes, mode: Literal["text", "binary"] = "text", encoding: str = "utf-8") -> None:
        """Sends a "receive" event. This is the inverse of the ASGI send method.

        Args:
            data: Either a string or a byte string.
            mode: The key to use - ``text`` or ``bytes``
            encoding: The encoding to use when encoding or decoding data.

        Returns:
            None.
        """
        if mode == "text":
            data = data.decode(encoding) if isinstance(data, bytes) else data
            text_event: WebSocketReceiveMessage = {"type": "websocket.receive", "text": data}  # type: ignore[assignment]
            await self._asgi_send(text_event)
        else:
            data = data if isinstance(data, bytes) else data.encode(encoding)
            binary_event: WebSocketReceiveMessage = {"type": "websocket.receive", "bytes": data}  # type: ignore[assignment]
            await self._asgi_send(binary_event)

    async def send_text(self, data: str, encoding: str = "utf-8") -> None:
        """Sends the data using the ``text`` key.

        Args:
            data: Data to send.
            encoding: Encoding to use.

        Returns:
            None
        """
        await self.send(data=data, encoding=encoding)

    async def send_bytes(self, data: bytes, encoding: str = "utf-8") -> None:
        """Sends the data using the ``bytes`` key.

        Args:
            data: Data to send.
            encoding: Encoding to use.

        Returns:
            None
        """
        await self.send(data=data, mode="binary", encoding=encoding)

    async def send_json(self, data: Any, mode: Literal["text", "binary"] = "text") -> None:
        """Sends the given data as JSON.

        Args:
            data: The data to send.
            mode: Either ``text`` or ``binary``

        Returns:
            None
        """
        await self.send(encode_json(data), mode=mode)

    async def send_msgpack(self, data: Any) -> None:
        """Sends the given data as MessagePack.

        Args:
            data: The data to send.

        Returns:
            None
        """
        await self.send(encode_msgpack(data), mode="binary")

    async def receive(self, block: bool = True, timeout: float | None = None) -> WebSocketSendMessage:
        """This is the base receive method.

        Args:
            block: Block until a message is received
            timeout: If ``block`` is ``True``, block at most ``timeout`` seconds

        Notes:
            - you can use one of the other receive methods to extract the data from the message.

        Returns:
            A websocket message.
        """
        message: WebSocketSendMessage | BaseException
        if not block:
            message = self._send_stream.receive_nowait()
        else:
            with anyio.fail_after(timeout):
                message = await self._send_stream.receive()

        if isinstance(message, BaseException):
            raise message

        if message["type"] == "websocket.close":
            raise WebSocketDisconnect(
                detail=cast("str", message.get("reason", "")),
                code=message.get("code", WS_1000_NORMAL_CLOSURE),
            )
        return message

    async def receive_text(self, block: bool = True, timeout: float | None = None) -> str:
        """Receive data in ``text`` mode and return a string

        Args:
            block: Block until a message is received
            timeout: If ``block`` is ``True``, block at most ``timeout`` seconds

        Returns:
            A string value.
        """
        message = await self.receive(block=block, timeout=timeout)
        return cast("str", message.get("text", ""))

    async def receive_bytes(self, block: bool = True, timeout: float | None = None) -> bytes:
        """Receive data in ``binary`` mode and return bytes

        Args:
            block: Block until a message is received
            timeout: If ``block`` is ``True``, block at most ``timeout`` seconds

        Returns:
            A string value.
        """
        message = await self.receive(block=block, timeout=timeout)
        return cast("bytes", message.get("bytes", b""))

    async def receive_json(
        self, mode: Literal["text", "binary"] = "text", block: bool = True, timeout: float | None = None
    ) -> Any:
        """Receive data in either ``text`` or ``binary`` mode and decode it as JSON.

        Args:
            mode: Either ``text`` or ``binary``
            block: Block until a message is received
            timeout: If ``block`` is ``True``, block at most ``timeout`` seconds

        Returns:
            An arbitrary value
        """
        message = await self.receive(block=block, timeout=timeout)

        if mode == "text":
            return decode_json(cast("str", message.get("text", "")))

        return decode_json(cast("bytes", message.get("bytes", b"")))

    async def receive_msgpack(self, block: bool = True, timeout: float | None = None) -> Any:
        message = await self.receive(block=block, timeout=timeout)
        return decode_msgpack(cast("bytes", message.get("bytes", b"")))
