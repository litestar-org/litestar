"""
Stress tests for AsyncWebSocketTestSession.

These tests verify that the async WebSocket implementation can handle:
- High message volume
- Concurrent connections
- Large message sizes
- Timeout handling
- Connection lifecycle stress
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest

from litestar import Litestar, websocket, websocket_stream
from litestar.connection import WebSocket
from litestar.testing import AsyncTestClient


@pytest.mark.asyncio
async def test_high_volume_messages():
    """Test sending/receiving many messages rapidly."""
    MESSAGE_COUNT = 1000

    @websocket("/volume")
    async def volume_handler(socket: WebSocket) -> None:
        await socket.accept()
        for i in range(MESSAGE_COUNT):
            data = await socket.receive_text()
            await socket.send_text(f"echo_{i}:{data}")
        await socket.close()

    app = Litestar(route_handlers=[volume_handler])

    async with AsyncTestClient(app=app) as client:
        async with await client.websocket_connect("/volume") as ws:
            # Send messages rapidly
            send_tasks = []
            for i in range(MESSAGE_COUNT):
                task = asyncio.create_task(ws.send_text(f"msg_{i}"))
                send_tasks.append(task)

            # Wait for all sends to complete
            await asyncio.gather(*send_tasks)

            # Receive all responses
            responses = []
            for i in range(MESSAGE_COUNT):
                response = await ws.receive_text()
                responses.append(response)

            # Verify all messages received correctly
            expected = [f"echo_{i}:msg_{i}" for i in range(MESSAGE_COUNT)]
            assert responses == expected


@pytest.mark.asyncio
async def test_concurrent_websocket_connections():
    """Test multiple concurrent WebSocket connections."""
    CONNECTION_COUNT = 50

    @websocket("/concurrent")
    async def concurrent_handler(socket: WebSocket) -> None:
        await socket.accept()
        # Get connection ID from query
        conn_id = socket.query_params.get("id", "unknown")
        await socket.send_text(f"Connected: {conn_id}")

        # Echo a few messages
        for i in range(10):
            data = await socket.receive_text()
            await socket.send_text(f"{conn_id}_{i}: {data}")

        await socket.close()

    app = Litestar(route_handlers=[concurrent_handler])

    async def handle_connection(client: AsyncTestClient, conn_id: int) -> list[str]:
        """Handle a single WebSocket connection."""
        responses = []
        async with await client.websocket_connect(f"/concurrent?id={conn_id}") as ws:
            # Get connection confirmation
            confirm = await ws.receive_text()
            responses.append(confirm)

            # Send and receive messages
            for i in range(10):
                await ws.send_text(f"message_{i}")
                response = await ws.receive_text()
                responses.append(response)

        return responses

    async with AsyncTestClient(app=app) as client:
        # Create multiple concurrent connections
        tasks = []
        for i in range(CONNECTION_COUNT):
            task = asyncio.create_task(handle_connection(client, i))
            tasks.append(task)

        # Wait for all connections to complete
        all_responses = await asyncio.gather(*tasks)

        # Verify all connections worked correctly
        assert len(all_responses) == CONNECTION_COUNT
        for i, responses in enumerate(all_responses):
            assert responses[0] == f"Connected: {i}"
            for j in range(10):
                expected = f"{i}_{j}: message_{j}"
                assert responses[j + 1] == expected


@pytest.mark.asyncio
async def test_large_message_handling():
    """Test handling of large messages."""
    LARGE_SIZE = 1024 * 1024  # 1MB

    @websocket("/large")
    async def large_handler(socket: WebSocket) -> None:
        await socket.accept()

        # Receive large message
        large_data = await socket.receive_text()

        # Send back size confirmation
        await socket.send_text(f"Received {len(large_data)} bytes")

        # Echo back the large message
        await socket.send_text(large_data)

        await socket.close()

    app = Litestar(route_handlers=[large_handler])
    large_message = "x" * LARGE_SIZE

    async with AsyncTestClient(app=app) as client:
        async with await client.websocket_connect("/large") as ws:
            # Send large message
            await ws.send_text(large_message)

            # Get size confirmation
            size_response = await ws.receive_text()
            assert size_response == f"Received {LARGE_SIZE} bytes"

            # Get echoed message
            echo_response = await ws.receive_text()
            assert echo_response == large_message


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test timeout behavior under stress."""

    @websocket("/timeout")
    async def timeout_handler(socket: WebSocket) -> None:
        await socket.accept()

        # Send immediate message
        await socket.send_text("immediate")

        # Wait before sending second message
        await asyncio.sleep(0.5)
        await socket.send_text("delayed")

        await socket.close()

    app = Litestar(route_handlers=[timeout_handler])

    async with AsyncTestClient(app=app) as client:
        async with await client.websocket_connect("/timeout") as ws:
            # Receive immediate message
            immediate = await ws.receive_text(timeout=1.0)
            assert immediate == "immediate"

            # Receive delayed message
            delayed = await ws.receive_text(timeout=1.0)
            assert delayed == "delayed"

            # Test timeout on no message - after close we get WebSocketDisconnect
            from litestar.exceptions import WebSocketDisconnect

            with pytest.raises(WebSocketDisconnect):
                await ws.receive_text(timeout=0.1)


@pytest.mark.asyncio
async def test_streaming_stress():
    """Test continuous streaming under stress."""
    STREAM_COUNT = 500

    @websocket_stream("/stream")
    async def stream_handler() -> AsyncGenerator[str, None]:
        for i in range(STREAM_COUNT):
            yield f"stream_message_{i}"
            # Small delay to test async handling
            await asyncio.sleep(0.001)

    app = Litestar(route_handlers=[stream_handler])

    async with AsyncTestClient(app=app) as client:
        async with await client.websocket_connect("/stream") as ws:
            messages = []

            # Collect all streamed messages
            for i in range(STREAM_COUNT):
                message = await ws.receive_text(timeout=5.0)
                messages.append(message)

            # Verify all messages received in order
            expected = [f"stream_message_{i}" for i in range(STREAM_COUNT)]
            assert messages == expected


@pytest.mark.asyncio
async def test_connection_lifecycle_stress():
    """Test rapid connection creation and destruction."""
    CONNECTION_CYCLES = 100

    @websocket("/lifecycle")
    async def lifecycle_handler(socket: WebSocket) -> None:
        await socket.accept()
        cycle_id = socket.query_params.get("cycle", "unknown")
        await socket.send_text(f"Cycle {cycle_id} active")
        await socket.close()

    app = Litestar(route_handlers=[lifecycle_handler])

    async with AsyncTestClient(app=app) as client:
        for i in range(CONNECTION_CYCLES):
            async with await client.websocket_connect(f"/lifecycle?cycle={i}") as ws:
                response = await ws.receive_text()
                assert response == f"Cycle {i} active"

            # After context exit, connection should be closed
            # Note: We can't test ws.is_closed() here as ws is out of scope


@pytest.mark.asyncio
async def test_mixed_message_types_stress():
    """Test mixing different message types under stress."""
    MESSAGE_SETS = 100

    @websocket("/mixed")
    async def mixed_handler(socket: WebSocket) -> None:
        await socket.accept()

        for i in range(MESSAGE_SETS):
            # Receive and echo text
            text_data = await socket.receive_text()
            await socket.send_text(f"text_{i}: {text_data}")

            # Receive and echo JSON
            json_data = await socket.receive_json()
            await socket.send_json({"json_response": i, "data": json_data})

            # Receive and echo bytes
            bytes_data = await socket.receive_bytes()
            await socket.send_bytes(f"bytes_{i}: ".encode() + bytes_data)

        await socket.close()

    app = Litestar(route_handlers=[mixed_handler])

    async with AsyncTestClient(app=app) as client:
        async with await client.websocket_connect("/mixed") as ws:
            for i in range(MESSAGE_SETS):
                # Send text
                await ws.send_text(f"text_message_{i}")
                text_response = await ws.receive_text()
                assert text_response == f"text_{i}: text_message_{i}"

                # Send JSON
                await ws.send_json({"key": f"value_{i}", "index": i})
                json_response = await ws.receive_json()
                expected_json = {"json_response": i, "data": {"key": f"value_{i}", "index": i}}
                assert json_response == expected_json

                # Send bytes
                await ws.send_bytes(f"bytes_data_{i}".encode())
                bytes_response = await ws.receive_bytes()
                expected_bytes = f"bytes_{i}: bytes_data_{i}".encode()
                assert bytes_response == expected_bytes


@pytest.mark.asyncio
async def test_error_handling_stress():
    """Test error handling under stress conditions."""

    @websocket("/error")
    async def error_handler(socket: WebSocket) -> None:
        await socket.accept()

        # Send a few normal messages
        for i in range(3):
            await socket.send_text(f"normal_{i}")

        # Simulate an error condition
        raise RuntimeError("Simulated error")

    app = Litestar(route_handlers=[error_handler])

    async with AsyncTestClient(app=app) as client:
        async with await client.websocket_connect("/error") as ws:
            # Receive normal messages
            for i in range(3):
                message = await ws.receive_text()
                assert message == f"normal_{i}"

            # Server will raise an error, which should result in connection being closed
            from litestar.exceptions import WebSocketDisconnect

            with pytest.raises(WebSocketDisconnect):
                await ws.receive_text(timeout=1.0)
