import asyncio
import time
from typing import Any, AsyncGenerator

from litestar import Litestar, WebSocket, websocket_stream


@websocket_stream("/")
async def ping(socket: WebSocket) -> AsyncGenerator[dict[str, Any], None]:
    while True:
        yield {"time": time.time(), "client": socket.client}
        await asyncio.sleep(0.5)


app = Litestar([ping])
