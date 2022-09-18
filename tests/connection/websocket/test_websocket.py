from typing import TYPE_CHECKING, Any

import pytest

from starlite import websocket
from starlite.connection import WebSocket
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from typing_extensions import Literal


@pytest.mark.parametrize("mode", ["text", "binary"])
def test_websocket_send_receive_json(mode: "Literal['text', 'binary']") -> None:
    @websocket(path="/")
    async def websocket_handler(socket: WebSocket) -> None:
        await socket.accept()
        recv = await socket.receive_json(mode=mode)
        await socket.send_json({"message": recv}, mode=mode)
        await socket.close()

    with create_test_client(route_handlers=[websocket_handler]).websocket_connect("/") as ws:
        ws.send_json({"hello": "world"}, mode=mode)
        data = ws.receive_json(mode=mode)
        assert data == {"message": {"hello": "world"}}


def test_route_handler_property() -> None:
    value: Any = {}

    @websocket("/")
    async def handler(socket: WebSocket) -> None:
        await socket.accept()
        value["handler"] = socket.route_handler
        await socket.close()

    with create_test_client(route_handlers=[handler]).websocket_connect("/"):
        assert value["handler"] is handler
