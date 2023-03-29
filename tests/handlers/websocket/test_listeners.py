from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_lazyfixture import lazy_fixture

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
