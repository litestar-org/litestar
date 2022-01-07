import pytest

from starlite import WebSocket, create_test_client, websocket


def test_websocket_handler_validation():
    def fn_without_socket_arg(websocket: WebSocket) -> None:
        pass

    with pytest.raises(AssertionError):
        websocket(path="/")(fn_without_socket_arg)

    def fn_with_return_annotation(socket: WebSocket) -> dict:
        return dict()

    with pytest.raises(AssertionError):
        websocket(path="/")(fn_with_return_annotation)


def test_handle_websocket():
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
