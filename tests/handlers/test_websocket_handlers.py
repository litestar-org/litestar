from typing import Any

import pytest

from starlite import (
    ImproperlyConfiguredException,
    Parameter,
    WebSocket,
    create_test_client,
    websocket,
)


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


def test_handle_websocket_params_parsing():
    @websocket(path="/{socket_id:int}")
    async def websocket_handler(
        socket: WebSocket,
        headers: dict,
        query: dict,
        cookies: dict,
        socket_id: int,
        qp: int,
        hp: str = Parameter(header="some-header"),
    ) -> None:
        assert socket_id
        assert headers
        assert query
        assert cookies
        assert qp
        assert hp
        await socket.accept()
        data = await socket.receive_json()
        assert data
        await socket.send_json({"data": "123"})
        await socket.close()

    client = create_test_client(route_handlers=websocket_handler)

    with client.websocket_connect("/1?qp=1", headers={"some-header": "abc"}, cookies={"cookie": "yum"}) as ws:
        ws.send_json({"data": "123"})
        data = ws.receive_json()
        assert data


def test_handle_websocket_params_validation():
    @websocket(path="/")
    async def websocket_handler_with_data_kwarg(socket: WebSocket, data: Any) -> None:
        await socket.accept()
        await socket.send_json({"data": "123"})
        await socket.close()

    client = create_test_client(route_handlers=websocket_handler_with_data_kwarg)

    with pytest.raises(ImproperlyConfiguredException), client.websocket_connect("/") as ws:
        ws.receive_json()

    @websocket(path="/")
    async def websocket_handler_with_request_kwarg(socket: WebSocket, request: Any) -> None:
        await socket.accept()
        await socket.send_json({"data": "123"})
        await socket.close()

    client = create_test_client(route_handlers=websocket_handler_with_request_kwarg)

    with pytest.raises(ImproperlyConfiguredException), client.websocket_connect("/") as ws:
        ws.receive_json()
