from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type, Union, cast
from unittest.mock import MagicMock

import pytest
from pytest_lazyfixture import lazy_fixture

from litestar import Litestar, Request, WebSocket
from litestar.datastructures import State
from litestar.di import Provide
from litestar.dto.factory import dto_field
from litestar.dto.factory.stdlib.dataclass import DataclassDTO
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers.websocket_handlers import WebsocketListener, websocket_listener
from litestar.testing import create_test_client
from litestar.types.asgi_types import WebSocketMode


@pytest.fixture
def mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def listener_class(mock: MagicMock) -> Type[WebsocketListener]:
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
def test_basic_listener(mock: MagicMock, listener: Union[websocket_listener, Type[WebsocketListener]]) -> None:
    client = create_test_client([listener])
    with client.websocket_connect("/") as ws:
        ws.send_text("foo")
        assert ws.receive_text() == "foo"
        ws.send_text("bar")
        assert ws.receive_text() == "bar"

    assert mock.call_count == 2
    mock.assert_any_call("foo")
    mock.assert_any_call("bar")


@pytest.mark.parametrize("receive_mode", ["text", "binary"])
def test_listener_receive_bytes(receive_mode: WebSocketMode, mock: MagicMock) -> None:
    @websocket_listener("/", receive_mode=receive_mode)
    def handler(data: bytes) -> None:
        mock(data)

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send("foo", mode=receive_mode)

    mock.assert_called_once_with(b"foo")


@pytest.mark.parametrize("receive_mode", ["text", "binary"])
def test_listener_receive_string(receive_mode: WebSocketMode, mock: MagicMock) -> None:
    @websocket_listener("/", receive_mode=receive_mode)
    def handler(data: str) -> None:
        mock(data)

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send("foo", mode=receive_mode)

    mock.assert_called_once_with("foo")


@pytest.mark.parametrize("receive_mode", ["text", "binary"])
def test_listener_receive_json(receive_mode: WebSocketMode, mock: MagicMock) -> None:
    @websocket_listener("/", receive_mode=receive_mode)
    def handler(data: List[str]) -> None:
        mock(data)

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_json(["foo", "bar"], mode=receive_mode)

    mock.assert_called_once_with(["foo", "bar"])


@pytest.mark.parametrize("receive_mode", ["text", "binary"])
def test_listener_receive_with_dto(receive_mode: WebSocketMode, mock: MagicMock) -> None:
    @dataclass
    class User:
        name: str
        hidden: str = field(default="super secret", metadata=dto_field("private"))

    user_dto = DataclassDTO[User]

    @websocket_listener(
        "/", receive_mode=receive_mode, dto=user_dto, return_dto=None, signature_namespace={"User": User}
    )
    def handler(data: User) -> None:
        mock(data)

    client = create_test_client([handler], debug=True, openapi_config=None)
    with client.websocket_connect("/") as ws:
        ws.send_json({"name": "litestar user", "hidden": "whoops"}, mode=receive_mode)

    called_with = mock.mock_calls[0].args[0]
    assert isinstance(called_with, User)
    assert called_with.name == "litestar user"
    assert called_with.hidden == "super secret"


@pytest.mark.parametrize("send_mode", ["text", "binary"])
def test_listener_return_bytes(send_mode: WebSocketMode) -> None:
    @websocket_listener("/", send_mode=send_mode)
    def handler(data: str) -> bytes:
        return data.encode("utf-8")

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("foo")
        if send_mode == "text":
            assert ws.receive_text() == "foo"
        else:
            assert ws.receive_bytes() == b"foo"


@pytest.mark.parametrize("send_mode", ["text", "binary"])
def test_listener_send_json(send_mode: WebSocketMode) -> None:
    @websocket_listener("/", send_mode=send_mode)
    def handler(data: str) -> Dict[str, str]:
        return {"data": data}

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("foo")
        assert ws.receive_json(mode=send_mode) == {"data": "foo"}


@pytest.mark.parametrize("send_mode", ["text", "binary"])
def test_listener_send_with_dto(send_mode: WebSocketMode, mock: MagicMock) -> None:
    @dataclass
    class User:
        name: str
        hidden: str = field(default="super secret", metadata=dto_field("private"))

    user_dto = DataclassDTO[User]

    @websocket_listener("/", send_mode=send_mode, dto=user_dto, signature_namespace={"User": User})
    def handler(data: User) -> User:
        return data

    client = create_test_client([handler], debug=True)
    with client.websocket_connect("/") as ws:
        ws.send_json({"name": "litestar user"})
        assert ws.receive_json(mode=send_mode) == {"name": "litestar user"}


def test_listener_return_none() -> None:
    @websocket_listener("/")
    def handler(data: str) -> None:
        return data  # type: ignore[return-value]

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("foo")


def test_listener_return_optional_none() -> None:
    @websocket_listener("/")
    def handler(data: str) -> Optional[str]:
        if data == "hello":
            return "world"
        return None

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("hello")
        assert ws.receive_text() == "world"
        ws.send_text("goodbye")


def test_listener_pass_socket(mock: MagicMock) -> None:
    @websocket_listener("/")
    def handler(data: str, socket: WebSocket) -> Dict[str, str]:
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
        return cast("int", state.foo)

    @websocket_listener("/", dependencies={"foo": Provide(foo_dependency)})
    def handler(data: str, foo: int) -> Dict[str, Union[str, int]]:
        return {"data": data, "foo": foo}

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        ws.send_text("something")
        ws.send_text("something")
        assert ws.receive_json() == {"data": "something", "foo": 1}


def test_listener_callback_no_data_arg_raises() -> None:
    with pytest.raises(ImproperlyConfiguredException):

        @websocket_listener("/")
        def handler() -> None:
            ...

        handler.on_registration(Litestar())


def test_listener_callback_request_and_body_arg_raises() -> None:
    with pytest.raises(ImproperlyConfiguredException):

        @websocket_listener("/")
        def handler_request(data: str, request: Request) -> None:
            ...

        handler_request.on_registration(Litestar())

    with pytest.raises(ImproperlyConfiguredException):

        @websocket_listener("/")
        def handler_body(data: str, body: bytes) -> None:
            ...

        handler_body.on_registration(Litestar())


def test_listener_accept_connection_callback() -> None:
    async def accept_connection(socket: WebSocket) -> None:
        await socket.accept(headers={"Cookie": "custom-cookie"})

    @websocket_listener("/", connection_accept_handler=accept_connection)
    def handler(data: bytes) -> None:
        return None

    client = create_test_client([handler])
    with client.websocket_connect("/") as ws:
        assert ws.extra_headers == [(b"cookie", b"custom-cookie")]
