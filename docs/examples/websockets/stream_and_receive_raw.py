from typing import Any, AsyncGenerator

import anyio

from litestar import Litestar, WebSocket, websocket
from litestar.exceptions import WebSocketDisconnect
from litestar.handlers import send_websocket_stream


@websocket("/")
async def handler(socket: WebSocket) -> None:
    await socket.accept()
    should_stop = anyio.Event()

    async def handle_stream() -> AsyncGenerator[str, None]:
        while not should_stop.is_set():
            await anyio.sleep(0.5)
            yield "ping"

    async def handle_receive() -> Any:
        await socket.send_json({"handle_receive": "start"})
        async for event in socket.iter_json():
            await socket.send_json(event)

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(send_websocket_stream, socket, handle_stream())
            tg.start_soon(handle_receive)
    except WebSocketDisconnect:
        should_stop.set()


app = Litestar([handler])
