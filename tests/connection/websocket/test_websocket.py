import pytest
from starlette.websockets import WebSocketDisconnect

from starlite import websocket
from starlite.connection import WebSocket
from starlite.testing import create_test_client


@pytest.mark.parametrize("mode", ["text", "binary"])
def test_websocket_send_receive_json(mode: str) -> None:
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


def test_websocket_receive_json_invalid_mode() -> None:
    @websocket(path="/")
    async def websocket_handler(socket: WebSocket) -> None:
        await socket.accept()
        await socket.receive_json(mode="weezer")

    with pytest.raises(WebSocketDisconnect) as exc, create_test_client(
        route_handlers=[websocket_handler]
    ).websocket_connect("/") as ws:
        ws.receive_json()

    assert (
        str(exc)
        == """<ExceptionInfo WebSocketDisconnect(4500, '500 - InternalServerException - The "mode" argument should be "text" or "binary".') tblen=3>"""
    )


def test_websocket_send_json_invalid_mode() -> None:
    @websocket(path="/")
    async def websocket_handler(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_json({"whoo": "psie"}, mode="matchbox 20")

    with pytest.raises(WebSocketDisconnect) as exc, create_test_client(
        route_handlers=[websocket_handler]
    ).websocket_connect("/") as ws:
        ws.receive_json()

    assert (
        str(exc)
        == """<ExceptionInfo WebSocketDisconnect(4500, '500 - InternalServerException - The "mode" argument should be "text" or "binary".') tblen=3>"""
    )


def test_websocket_receive_without_accept() -> None:
    @websocket(path="/")
    async def websocket_handler(socket: WebSocket) -> None:
        await socket.receive_json()

    with pytest.raises(WebSocketDisconnect) as exc, create_test_client(
        route_handlers=[websocket_handler]
    ).websocket_connect("/") as ws:
        ws.send_json({"bad": "server"})

    assert (
        str(exc)
        == """<ExceptionInfo WebSocketDisconnect(4500, '500 - InternalServerException - WebSocket is not connected. Need to call "accept" first.') tblen=3>"""
    )
