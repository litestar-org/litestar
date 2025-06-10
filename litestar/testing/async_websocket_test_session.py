"""
Fully async WebSocket test session implementation.

This is a complete rewrite with true async architecture:
- asyncio.Queue for all communication
- Proper cancellation support
- Backpressure handling
- Event-driven design
- No polling or blocking operations
- STRICTLY ASYNC ONLY - no sync compatibility methods
"""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any, Literal, cast

from litestar.exceptions import WebSocketDisconnect
from litestar.serialization import decode_json, decode_msgpack, encode_json, encode_msgpack
from litestar.status_codes import WS_1000_NORMAL_CLOSURE

if TYPE_CHECKING:
    from litestar.testing.client.async_client import AsyncTestClient
    from litestar.types import (
        WebSocketConnectEvent,
        WebSocketDisconnectEvent,
        WebSocketReceiveMessage,
        WebSocketScope,
        WebSocketSendMessage,
    )


__all__ = ("AsyncWebSocketTestSession",)


class AsyncWebSocketTestSession:
    """Fully async WebSocket test session - ASYNC ONLY."""

    def __init__(
        self,
        client: AsyncTestClient,
        scope: WebSocketScope,
    ) -> None:
        self.client = client
        self.scope = scope
        self.accepted_subprotocol: str | None = None
        self.extra_headers: list[tuple[bytes, bytes]] | None = None
        
        # Pure async queues
        self.receive_queue: asyncio.Queue[WebSocketReceiveMessage] = asyncio.Queue()
        self.send_queue: asyncio.Queue[WebSocketSendMessage | BaseException] = asyncio.Queue()
        
        # Event-driven coordination
        self.connection_ready = asyncio.Event()
        self.connection_closed = asyncio.Event()
        
        # Task management for proper cleanup
        self.asgi_task: asyncio.Task[None] | None = None
        self.exit_stack: AsyncExitStack | None = None

    async def __aenter__(self) -> AsyncWebSocketTestSession:
        """Async context manager entry - true async initialization."""
        self.exit_stack = AsyncExitStack()
        
        try:
            # Start ASGI application in background task
            self.asgi_task = asyncio.create_task(self._run_asgi_app())
            
            # Send connection event
            connect_event: WebSocketConnectEvent = {"type": "websocket.connect"}
            await self.receive_queue.put(connect_event)
            
            # Wait for connection to be established (with timeout)
            try:
                await asyncio.wait_for(self.connection_ready.wait(), timeout=self.client.timeout.read)
            except asyncio.TimeoutError:
                raise TimeoutError("WebSocket connection timeout")
            
            # Get the accept message
            message = await self.receive(timeout=self.client.timeout.read)
            self.accepted_subprotocol = cast("str | None", message.get("subprotocol"))
            self.extra_headers = cast("list[tuple[bytes, bytes]] | None", message.get("headers"))
            
            return self
            
        except Exception:
            await self._cleanup()
            raise

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit with proper cleanup."""
        await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up resources properly."""
        try:
            # Signal close if not already closed
            if not self.connection_closed.is_set():
                await self.close()
                
            # Cancel ASGI task
            if self.asgi_task and not self.asgi_task.done():
                self.asgi_task.cancel()
                try:
                    await self.asgi_task
                except asyncio.CancelledError:
                    pass
                    
        finally:
            if self.exit_stack:
                await self.exit_stack.aclose()

    async def _run_asgi_app(self) -> None:
        """Run ASGI application with proper async handling."""
        
        async def receive() -> WebSocketReceiveMessage:
            """Async receive from test client."""
            return await self.receive_queue.get()

        async def send(message: WebSocketSendMessage) -> None:
            """Async send to test client."""
            # Handle connection acceptance
            if message["type"] == "websocket.accept":
                headers = message.get("headers", [])
                if headers:
                    headers_list = list(self.scope["headers"])
                    headers_list.extend(headers)
                    self.scope["headers"] = headers_list
                    
                subprotocols = cast("str | None", message.get("subprotocols"))
                if subprotocols:
                    self.scope["subprotocols"].append(subprotocols)
                    
                # Signal that connection is ready
                self.connection_ready.set()
            
            # Handle connection close
            elif message["type"] == "websocket.close":
                self.connection_closed.set()
            
            # Put message in send queue
            await self.send_queue.put(message)

        try:
            await self.client.app(self.scope, receive, send)
        except BaseException as exc:
            await self.send_queue.put(exc)
            raise

    # === Send methods (client -> server) ===
    
    async def send(self, data: str | bytes, mode: Literal["text", "binary"] = "text", encoding: str = "utf-8") -> None:
        """Send data to WebSocket."""
        if mode == "text":
            data = data.decode(encoding) if isinstance(data, bytes) else data
            event: WebSocketReceiveMessage = {"type": "websocket.receive", "text": data}
        else:
            data = data if isinstance(data, bytes) else data.encode(encoding)
            event = {"type": "websocket.receive", "bytes": data}
            
        await self.receive_queue.put(event)

    async def send_text(self, data: str, encoding: str = "utf-8") -> None:
        """Send text data."""
        await self.send(data=data, mode="text", encoding=encoding)

    async def send_bytes(self, data: bytes, encoding: str = "utf-8") -> None:
        """Send binary data."""
        await self.send(data=data, mode="binary", encoding=encoding)

    async def send_json(self, data: Any, mode: Literal["text", "binary"] = "text") -> None:
        """Send JSON data."""
        await self.send(encode_json(data), mode=mode)

    async def send_msgpack(self, data: Any) -> None:
        """Send MessagePack data."""
        await self.send(encode_msgpack(data), mode="binary")

    async def close(self, code: int = WS_1000_NORMAL_CLOSURE) -> None:
        """Close WebSocket connection."""
        event: WebSocketDisconnectEvent = {"type": "websocket.disconnect", "code": code}
        await self.receive_queue.put(event)
        self.connection_closed.set()

    # === Receive methods (server -> client) ===

    async def receive(self, timeout: float | None = None) -> WebSocketSendMessage:
        """Receive message from WebSocket with proper timeout handling."""
        try:
            if timeout is not None:
                message = await asyncio.wait_for(self.send_queue.get(), timeout=timeout)
            else:
                message = await self.send_queue.get()
                
        except asyncio.TimeoutError:
            from queue import Empty
            raise Empty()

        if isinstance(message, BaseException):
            raise message

        if message["type"] == "websocket.close":
            self.connection_closed.set()
            raise WebSocketDisconnect(
                detail=cast("str", message.get("reason", "")),
                code=message.get("code", WS_1000_NORMAL_CLOSURE),
            )
            
        return message

    async def receive_text(self, timeout: float | None = None) -> str:
        """Receive text message."""
        message = await self.receive(timeout=timeout)
        return cast("str", message.get("text", ""))

    async def receive_bytes(self, timeout: float | None = None) -> bytes:
        """Receive binary message."""
        message = await self.receive(timeout=timeout)
        return cast("bytes", message.get("bytes", b""))

    async def receive_json(
        self, mode: Literal["text", "binary"] = "text", timeout: float | None = None
    ) -> Any:
        """Receive JSON message."""
        message = await self.receive(timeout=timeout)
        if mode == "text":
            return decode_json(cast("str", message.get("text", "")))
        return decode_json(cast("bytes", message.get("bytes", b"")))

    async def receive_msgpack(self, timeout: float | None = None) -> Any:
        """Receive MessagePack message."""
        message = await self.receive(timeout=timeout)
        return decode_msgpack(cast("bytes", message.get("bytes", b"")))

    # === Status methods ===
    
    def is_connected(self) -> bool:
        """Check if connection is established."""
        return self.connection_ready.is_set() and not self.connection_closed.is_set()
        
    def is_closed(self) -> bool:
        """Check if connection is closed."""
        return self.connection_closed.is_set()
        
    async def wait_closed(self, timeout: float | None = None) -> None:
        """Wait for connection to close."""
        if timeout is not None:
            await asyncio.wait_for(self.connection_closed.wait(), timeout=timeout)
        else:
            await self.connection_closed.wait() 