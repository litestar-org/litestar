"""
Minimal Complete Verifiable Example (MCVE) demonstrating WebSocket testing issue.

The async test client does not connect and allow testing websockets.
The sync client works as expected.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest

from litestar import Litestar, websocket, websocket_stream
from litestar.connection import WebSocket
from litestar.testing import AsyncTestClient, TestClient


@websocket_stream("/ws")
async def websocket_handler() -> AsyncGenerator[str, None]:
    """Simple WebSocket handler that yields messages."""
    for i in range(3):
        yield f"message_{i}"
        await asyncio.sleep(0.1)


@websocket("/simple")
async def simple_websocket_handler(socket: WebSocket) -> None:
    """Simple WebSocket handler for basic testing."""
    await socket.accept()
    await socket.send_text("Hello WebSocket!")
    await socket.close()


app = Litestar(route_handlers=[websocket_handler])
simple_app = Litestar(route_handlers=[simple_websocket_handler])


@pytest.fixture
def sync_client() -> TestClient:
    return TestClient(app=app)


@pytest.fixture
def async_client() -> AsyncTestClient:
    return AsyncTestClient(app=app)


def test_websocket_with_sync_client(
    sync_client: TestClient,
) -> None:
    """This test passes - sync client works with WebSockets."""
    with sync_client as client:
        with client.websocket_connect("/ws") as ws:
            message1 = ws.receive_text()
            assert message1 == "message_0"

            message2 = ws.receive_text()
            assert message2 == "message_1"


async def test_websocket_with_async_client(
    async_client: AsyncTestClient,
) -> None:
    """This test should work - async client with async WebSocket context manager support."""
    async with async_client as client:
        async with await client.websocket_connect("/ws") as ws:
            message1 = await ws.receive_text()
            assert message1 == "message_0"

            message2 = await ws.receive_text()
            assert message2 == "message_1"


@pytest.mark.asyncio
async def test_async_websocket_with_context_manager():
    """Test that AsyncTestClient can use AsyncWebSocketTestSession with async context manager."""
    async with AsyncTestClient(app=simple_app) as client:
        # This should now work with AsyncWebSocketTestSession
        async with await client.websocket_connect("/simple") as ws:
            message = await ws.receive_text()
            assert message == "Hello WebSocket!"


@pytest.mark.asyncio
async def test_async_websocket_send_receive():
    """Test sending and receiving data through async WebSocket."""

    @websocket("/echo")
    async def echo_handler(socket: WebSocket) -> None:
        await socket.accept()
        data = await socket.receive_text()
        await socket.send_text(f"Echo: {data}")
        await socket.close()

    app_echo = Litestar(route_handlers=[echo_handler])

    async with AsyncTestClient(app=app_echo) as client:
        async with await client.websocket_connect("/echo") as ws:
            await ws.send_text("Hello")
            response = await ws.receive_text()
            assert response == "Echo: Hello"


@pytest.mark.asyncio
async def test_async_websocket_json():
    """Test JSON communication through async WebSocket."""

    @websocket("/json")
    async def json_handler(socket: WebSocket) -> None:
        await socket.accept()
        data = await socket.receive_json()
        await socket.send_json({"response": data["message"]})
        await socket.close()

    app_json = Litestar(route_handlers=[json_handler])

    async with AsyncTestClient(app=app_json) as client:
        async with await client.websocket_connect("/json") as ws:
            await ws.send_json({"message": "test"})
            response = await ws.receive_json()
            assert response == {"response": "test"}


@pytest.mark.asyncio
async def test_async_websocket_multiple_messages():
    """Test multiple message exchange through async WebSocket."""

    @websocket("/multi")
    async def multi_handler(socket: WebSocket) -> None:
        await socket.accept()
        for i in range(5):
            data = await socket.receive_text()
            await socket.send_text(f"Message {i}: {data}")
        await socket.close()

    app_multi = Litestar(route_handlers=[multi_handler])

    async with AsyncTestClient(app=app_multi) as client:
        async with await client.websocket_connect("/multi") as ws:
            messages = []
            for i in range(5):
                await ws.send_text(f"msg_{i}")
                response = await ws.receive_text()
                messages.append(response)

            assert messages == [f"Message {i}: msg_{i}" for i in range(5)]


@pytest.mark.asyncio
async def test_async_websocket_connection_status():
    """Test connection status methods."""

    @websocket("/status_test")
    async def status_handler(socket: WebSocket) -> None:
        await socket.accept()
        # Send a message but keep connection open for a bit
        await socket.send_text("Connected and ready")
        # Wait for client to check status
        await socket.receive_text()  # Wait for "check_status" message
        await socket.send_text("Still connected")
        await socket.close()

    status_app = Litestar(route_handlers=[status_handler])

    async with AsyncTestClient(app=status_app) as client:
        async with await client.websocket_connect("/status_test") as ws:
            # Initially should be connected after accept
            assert ws.is_connected()
            assert not ws.is_closed()

            # Receive initial message
            message = await ws.receive_text()
            assert message == "Connected and ready"

            # Should still be connected
            assert ws.is_connected()
            assert not ws.is_closed()

            # Send a message to trigger server response
            await ws.send_text("check_status")
            response = await ws.receive_text()
            assert response == "Still connected"

            # After server closes, connection should be closed
            # The close happens when the handler completes
            assert ws.is_closed()
            assert not ws.is_connected()
