from typing import Any

from litestar import WebSocket, websocket
from litestar.datastructures import State
from litestar.testing import create_test_client


async def test_websocket() -> None:
    @websocket(path="/ws")
    async def websocket_handler(socket: WebSocket[Any, Any, State]) -> None:
        await socket.accept()
        recv = await socket.receive_json()
        await socket.send_json({"message": recv})
        await socket.close()

    async with create_test_client(route_handlers=[websocket_handler]) as client:
        async with await client.websocket_connect("/ws") as ws:
            ws.send_json({"hello": "world"})
            data = ws.receive_json()
            assert data == {"message": {"hello": "world"}}
