"""
Minimal Complete Verifiable Example (MCVE) demonstrating WebSocket testing issue.

The async test client does not connect and allow testing websockets.
The sync client works as expected.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest

from litestar import Litestar, websocket_stream
from litestar.testing import AsyncTestClient, TestClient


@websocket_stream("/ws")
async def websocket_handler() -> AsyncGenerator[str, None]:
    """Simple WebSocket handler that yields messages."""
    for i in range(3):
        yield f"message_{i}"
        await asyncio.sleep(0.1)


app = Litestar(route_handlers=[websocket_handler])


@pytest.fixture
def sync_client() -> TestClient[Any]:
    return TestClient(app=app)


@pytest.fixture
def async_client() -> AsyncTestClient[Any]:
    return AsyncTestClient(app=app)


def test_websocket_with_sync_client(
    sync_client: TestClient[Any],
) -> None:
    """This test passes - sync client works with WebSockets."""
    with sync_client as client:
        with client.websocket_connect("/ws") as ws:
            message1 = ws.receive_text()
            assert message1 == "message_0"

            message2 = ws.receive_text()
            assert message2 == "message_1"


async def test_websocket_with_async_client(
    async_client: AsyncTestClient[Any],
) -> None:
    """This test should work - async client with proper await for WebSockets."""
    async with async_client as client:
        async with await client.websocket_connect("/ws") as ws:
            message1 = await ws.areceive_text()
            assert message1 == "message_0"

            message2 = await ws.areceive_text()
            assert message2 == "message_1"
