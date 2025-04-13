import asyncio
import datetime
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from litestar import Litestar, WebSocket, websocket_listener
from litestar.handlers import send_websocket_stream


@asynccontextmanager
async def listener_lifespan(socket: WebSocket) -> AsyncGenerator[None, Any]:
    async def handle_stream() -> AsyncGenerator[str, None]:
        while True:
            await asyncio.sleep(0.5)
            yield datetime.datetime.now(datetime.UTC).isoformat()
            await asyncio.sleep(0.5)

    task = asyncio.create_task(send_websocket_stream(socket=socket, stream=handle_stream()))
    yield
    task.cancel()
    await task


@websocket_listener("/", connection_lifespan=listener_lifespan)
def handler(socket: WebSocket, data: str) -> str:
    return data


app = Litestar([handler])
