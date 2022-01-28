from asyncio import sleep
from typing import Any, Dict

import pytest
from starlette.websockets import WebSocketDisconnect

from starlite import Controller, Provide, create_test_client, websocket
from starlite.connection import WebSocket


def router_first_dependency():
    return True


async def router_second_dependency():
    await sleep(0.1)
    return False


def controller_first_dependency(headers: Dict[str, Any]):
    assert headers
    return dict()


async def controller_second_dependency(socket: WebSocket):
    assert socket
    await sleep(0.1)
    return dict()


def local_method_first_dependency(query_param: int):
    assert isinstance(query_param, int)
    return query_param


def local_method_second_dependency(path_param: str):
    assert isinstance(path_param, str)
    return path_param


test_path = "/test"


class FirstController(Controller):
    path = test_path
    dependencies = {"first": Provide(controller_first_dependency), "second": Provide(controller_second_dependency)}

    @websocket(
        path="/{path_param:str}",
        dependencies={
            "first": Provide(local_method_first_dependency),
        },
    )
    async def test_method(self, socket: WebSocket, first: int, second: dict, third: bool) -> None:
        await socket.accept()
        msg = await socket.receive_json()
        assert msg
        assert socket
        assert isinstance(first, int)
        assert isinstance(second, dict)
        assert third is False
        await socket.close()


def test_controller_dependency_injection():
    client = create_test_client(
        FirstController,
        dependencies={
            "second": Provide(router_first_dependency),
            "third": Provide(router_second_dependency),
        },
    )
    with client.websocket_connect(f"{test_path}/abcdef?query_param=12345") as ws:
        ws.send_json({"data": "123"})


def test_function_dependency_injection():
    @websocket(
        path=test_path + "/{path_param:str}",
        dependencies={
            "first": Provide(local_method_first_dependency),
            "third": Provide(local_method_second_dependency),
        },
    )
    async def test_function(socket: WebSocket, first: int, second: bool, third: str) -> None:
        await socket.accept()
        assert socket
        msg = await socket.receive_json()
        assert msg
        assert isinstance(first, int)
        assert second is False
        assert isinstance(third, str)
        await socket.close()

    client = create_test_client(
        test_function,
        dependencies={
            "first": Provide(router_first_dependency),
            "second": Provide(router_second_dependency),
        },
    )
    with client.websocket_connect(f"{test_path}/abcdef?query_param=12345") as ws:
        ws.send_json({"data": "123"})


def test_dependency_isolation():
    class SecondController(Controller):
        path = "/second"

        @websocket()
        async def test_method(self, socket: WebSocket, first: dict) -> None:
            await socket.accept()
            assert socket
            msg = await socket.receive_json()
            assert msg
            assert isinstance(first, int)
            await socket.close()

    client = create_test_client([FirstController, SecondController])
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/second/abcdef?query_param=12345") as ws:
        ws.send_json({"data": "123"})
