from __future__ import annotations

from litestar import WebSocket, websocket
from litestar.testing import create_test_client


def test_handle_websocket() -> None:
    @websocket(path="/")
    async def simple_websocket_handler(socket: WebSocket) -> None:
        await socket.accept()
        data = await socket.receive_json()
        assert data
        await socket.send_json({"data": "123"})
        await socket.close()

    client = create_test_client(route_handlers=simple_websocket_handler)

    with client.websocket_connect("/") as ws:
        ws.send_json({"data": "123"})
        data = ws.receive_json()
        assert data
