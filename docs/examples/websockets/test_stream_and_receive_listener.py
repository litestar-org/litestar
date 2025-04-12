import asyncio
import datetime
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from time_machine import travel

from litestar import Litestar, WebSocket, websocket_listener
from litestar.handlers import send_websocket_stream
from litestar.testing import AsyncTestClient


@asynccontextmanager
async def listener_lifespan(socket: WebSocket) -> AsyncGenerator[None, Any]:
    async def handle_stream() -> AsyncGenerator[str, None]:
        while True:
            yield datetime.datetime.now(datetime.UTC).isoformat()
            await asyncio.sleep(0.5)

    task = asyncio.create_task(send_websocket_stream(socket=socket, stream=handle_stream()))
    yield
    task.cancel()
    await task


@websocket_listener("/", connection_lifespan=listener_lifespan)
async def handler(socket: WebSocket, data: str) -> str:
    return data


app = Litestar([handler])


@travel(datetime.datetime.now(datetime.UTC), tick=False)
async def test_websocket_listener() -> None:
    """Test the websocket listener."""
    async with AsyncTestClient(app) as client:
        with await client.websocket_connect("/") as ws:
            ws.send_text("Hello")
            data = ws.receive_text()
            assert data == datetime.datetime.now(datetime.UTC).isoformat()
            data = ws.receive_text()
            assert data == "Hello"
