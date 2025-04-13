import asyncio
import datetime
from typing import Any, AsyncGenerator

from litestar import Litestar, WebSocket, websocket
from litestar.handlers import send_websocket_stream


@websocket("/")
async def handler(socket: WebSocket) -> None:
    await socket.accept()

    async def handle_stream() -> AsyncGenerator[str, None]:
        while True:
            yield datetime.datetime.now(datetime.UTC).isoformat()
            await asyncio.sleep(2)

    async def handle_receive() -> Any:
        await socket.send_json({"handle_receive": "start"})
        async for event in socket.iter_json():
            print(f"event: {event}")
            await socket.send_json(event)

        print("end")
        await socket.send_json({"handle_receive": "end"})

    async with asyncio.TaskGroup() as tg:
        tg.create_task(send_websocket_stream(socket=socket, stream=handle_stream()))
        tg.create_task(handle_receive())


app = Litestar([handler])
