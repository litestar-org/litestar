from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_lazyfixture import lazy_fixture

from starlite import WebSocket
from starlite.datastructures import State
from starlite.di import Provide
from starlite.handlers.websocket_handlers import WebsocketListener, websocket_listener
from starlite.testing import create_test_client


@pytest.fixture
def mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def listener_class(mock: MagicMock) -> type[WebsocketListener]:
    class Listener(WebsocketListener):
        def on_receive(self, data: str) -> str:
            mock(data)
            return data

    return Listener


@pytest.fixture
def sync_listener_callable(mock: MagicMock) -> websocket_listener:
    def listener(data: str) -> str:
        mock(data)
        return data

    return websocket_listener("/")(listener)


@pytest.fixture
def async_listener_callable(mock: MagicMock) -> websocket_listener:
    async def listener(data: str) -> str:
        mock(data)
        return data

    return websocket_listener("/")(listener)


@pytest.mark.parametrize(
    "listener",
    [
        lazy_fixture("sync_listener_callable"),
        lazy_fixture("async_listener_callable"),
        lazy_fixture("listener_class"),
    ],
)
def test_basic_listener(mock: MagicMock, listener: websocket_listener | type[WebsocketListener]) -> None:
    client = create_test_client([listener])
    with client.websocket_connect("/") as ws:
        ws.send_text("foo")
        assert ws.receive_text() == "foo"
        ws.send_text("bar")
        assert ws.receive_text() == "bar"

    assert mock.call_count == 2
    mock.assert_any_call("foo")
    mock.assert_any_call("bar")


def test_listener_receive_bytes(mock: MagicMock) -> None:
    @websocket_listener("/", mode="binary")
    def handler(data: bytes) -> None:
        mock(data)

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_bytes(b"foo")

    mock.assert_called_once_with(b"foo")


def test_listener_receive_json(mock: MagicMock) -> None:
    @websocket_listener("/")
    def handler(data: list[str]) -> None:
        mock(data)

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_json(["foo", "bar"])

    mock.assert_called_once_with(["foo", "bar"])


def test_listener_send_bytes() -> None:
    @websocket_listener("/")
    def handler(data: str) -> bytes:
        return data.encode("utf-8")

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("foo")
        assert ws.receive_bytes() == b"foo"


def test_listener_send_json() -> None:
    @websocket_listener("/")
    def handler(data: str) -> dict[str, str]:
        return {"data": data}

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("foo")
        assert ws.receive_json() == {"data": "foo"}


def test_listener_pass_socket(mock: MagicMock) -> None:
    @websocket_listener("/")
    def handler(data: str, socket: WebSocket) -> dict[str, str]:
        mock(socket=socket)
        return {"data": data}

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("foo")
        assert ws.receive_json() == {"data": "foo"}

    assert isinstance(mock.call_args.kwargs["socket"], WebSocket)


def test_listener_pass_additional_dependencies(mock: MagicMock) -> None:
    def foo_dependency(state: State) -> int:
        if not hasattr(state, "foo"):
            state.foo = 0
        state.foo += 1
        return state.foo

    @websocket_listener("/", dependencies={"foo": Provide(foo_dependency)})
    def handler(data: str, foo: int) -> dict[str, str | int]:
        return {"data": data, "foo": foo}

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("something")
        ws.send_text("something")
        assert ws.receive_json() == {"data": "something", "foo": 1}
