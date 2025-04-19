from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import anyio

from litestar import Litestar, WebSocket, websocket_listener
from litestar.exceptions import WebSocketDisconnect
from litestar.handlers import send_websocket_stream


@asynccontextmanager
async def listener_lifespan(socket: WebSocket) -> AsyncGenerator[None, Any]:
    is_closed = anyio.Event()

    async def handle_stream() -> AsyncGenerator[str, None]:
        while not is_closed.is_set():
            await anyio.sleep(0.1)
            yield "ping"

    async with anyio.create_task_group() as tg:
        tg.start_soon(send_websocket_stream, socket, handle_stream())

        try:
            yield
        except WebSocketDisconnect:
            pass
        finally:
            is_closed.set()


@websocket_listener("/", connection_lifespan=listener_lifespan)
def handler(data: str) -> str:
    return data


app = Litestar([handler])
