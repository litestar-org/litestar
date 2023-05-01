from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.fixtures import FixtureRequest

from litestar import Litestar, WebSocket, get, websocket
from litestar.channels import ChannelsBackend, ChannelsPlugin
from litestar.channels.memory import MemoryChannelsBackend
from litestar.exceptions import ImproperlyConfiguredException, LitestarException
from litestar.testing import TestClient, create_test_client
from litestar.types.asgi_types import WebSocketMode

pytestmark = [pytest.mark.usefixtures("redis_service")]


@pytest.fixture
def mock() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def async_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(
    params=[
        pytest.param("memory_backend", id="memory"),
        pytest.param("redis_stream_backend", id="redis:stream"),
        pytest.param("redis_pub_sub_backend", id="redis:pubsub"),
    ]
)
async def channels_backend(request: FixtureRequest) -> ChannelsBackend:
    return cast(ChannelsBackend, request.getfixturevalue(request.param))


def test_channels_no_channels_arbitrary_not_allowed_raises(memory_backend: MemoryChannelsBackend) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ChannelsPlugin(backend=memory_backend)


@pytest.mark.parametrize("socket_send_mode", ["text", "binary"])
async def test_pub_sub(channels_backend: ChannelsBackend, socket_send_mode: WebSocketMode) -> None:
    @websocket("/")
    async def handler(socket: WebSocket, channels: ChannelsPlugin) -> None:
        await socket.accept()
        async with channels.start_subscription(socket, "something"):
            while True:
                await socket.receive()

    channels_plugin = ChannelsPlugin(
        backend=channels_backend, channels=["something"], socket_send_mode=socket_send_mode
    )
    app = Litestar([handler], plugins=[channels_plugin])

    with TestClient(app) as client, client.websocket_connect("/") as ws:
        channels_plugin.broadcast(["foo"], "something")
        assert ws.receive_json(mode=socket_send_mode, timeout=1) == ["foo"]


@pytest.mark.parametrize("socket_send_mode", ["text", "binary"])
@pytest.mark.parametrize("handler_base_path", [None, "/ws"])
def test_pub_sub_create_route_handlers(
    channels_backend: ChannelsBackend, handler_base_path: str | None, socket_send_mode: WebSocketMode
) -> None:
    channels_plugin = ChannelsPlugin(
        backend=channels_backend,
        create_route_handlers=True,
        channels=["something"],
        handler_base_path=handler_base_path or "/",
        socket_send_mode=socket_send_mode,
    )
    app = Litestar(plugins=[channels_plugin])

    with TestClient(app) as client, client.websocket_connect(f"{handler_base_path or ''}/something") as ws:
        channels_plugin.broadcast(["foo"], "something")
        assert ws.receive_json(mode=socket_send_mode, timeout=0.1) == ["foo"]


async def test_create_route_handlers_arbitrary_channels_allowed(channels_backend: ChannelsBackend) -> None:
    channels_plugin = ChannelsPlugin(
        backend=channels_backend, arbitrary_channels_allowed=True, create_route_handlers=True, handler_base_path="/ws"
    )

    app = Litestar(plugins=[channels_plugin])

    with TestClient(app) as client:
        with client.websocket_connect("/ws/foo") as ws:
            channels_plugin.broadcast("something", "foo")
            assert ws.receive_text(timeout=1) == "something"

        with client.websocket_connect("/ws/bar") as ws:
            channels_plugin.broadcast("something else", "bar")
            assert ws.receive_text(timeout=1) == "something else"


def test_plugin_dependency(mock: MagicMock, memory_backend: MemoryChannelsBackend) -> None:
    @get()
    def handler(channels: ChannelsPlugin) -> None:
        mock(channels)

    channels_plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)

    with create_test_client(handler, plugins=[channels_plugin]) as client:
        res = client.get("/")
        assert res.status_code == 200

    assert mock.call_count == 1
    assert mock.call_args[0][0] is channels_plugin


@pytest.mark.parametrize("arbitrary_channels_allowed", [True, False])
@pytest.mark.parametrize("channels", ["foo", ["foo", "bar"]])
async def test_subscribe(
    async_mock: AsyncMock,
    memory_backend: MemoryChannelsBackend,
    channels: str | list[str],
    arbitrary_channels_allowed: bool,
) -> None:
    plugin = ChannelsPlugin(
        backend=memory_backend,
        channels=["foo", "bar"] if not arbitrary_channels_allowed else None,
        arbitrary_channels_allowed=arbitrary_channels_allowed,
    )
    memory_backend.subscribe = async_mock  # type: ignore[method-assign]
    socket = MagicMock()

    await plugin.subscribe(socket=socket, channels=channels)

    if isinstance(channels, str):
        channels = [channels]

    for channel in channels:
        subscribers = plugin._channels.get(channel)
        assert subscribers
        assert socket in subscribers

    async_mock.assert_called_once_with(set(channels))


async def test_subscribe_non_existent_channel_raises(memory_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, channels=["foo"])

    with pytest.raises(LitestarException):
        await plugin.subscribe(MagicMock(), "bar")


@pytest.mark.parametrize("channels", ["foo", ["foo", "bar"]])
async def test_unsubscribe(
    async_mock: AsyncMock,
    memory_backend: MemoryChannelsBackend,
    channels: str | list[str],
) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, channels=["foo", "bar"])
    memory_backend.unsubscribe = async_mock  # type: ignore[method-assign]
    socket_1 = MagicMock()
    socket_2 = MagicMock()
    await plugin.subscribe(socket=socket_1, channels=channels)
    await plugin.subscribe(socket=socket_2, channels=channels)

    await plugin.unsubscribe(socket=socket_1, channels=channels)

    if isinstance(channels, str):
        channels = [channels]

    assert async_mock.call_count == 0

    for channel in channels:
        subscribers = plugin._channels.get(channel)
        assert subscribers
        assert socket_2 in subscribers


async def test_unsubscribe_last_subscriber_unsubscribes_backend(
    memory_backend: MemoryChannelsBackend, async_mock: AsyncMock
) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, channels=["foo"])
    memory_backend.unsubscribe = async_mock  # type: ignore[method-assign]
    socket_1 = MagicMock()
    socket_2 = MagicMock()
    await plugin.subscribe(socket=socket_1, channels="foo")
    await plugin.subscribe(socket=socket_2, channels="foo")

    await plugin.unsubscribe(socket=socket_1, channels="foo")
    await plugin.unsubscribe(socket=socket_2, channels="foo")

    assert async_mock.call_count == 1

    assert not plugin._channels.get("foo")


async def _populate_channels_backend(*, message_count: int, channel: str, backend: ChannelsBackend) -> list[bytes]:
    messages = [f"message {i}".encode() for i in range(message_count)]

    for message in messages:
        await backend.publish(message, [channel])
    await backend.publish(b"some other message", ["bar"])
    return messages


class MockPluginHandleSocketSend(AsyncMock):
    def get_data_call_args(self, ordered: bool) -> list[bytes]:
        call_args = [call.args[1] for call in self.call_args_list]
        if not ordered:
            call_args = sorted(call_args)
        return call_args


@pytest.mark.parametrize("chronological_order", [True, False])
@pytest.mark.parametrize(
    "message_count,history_limit,expected_history_count",
    [
        (2, None, 2),
        (2, 1, 1),
        (2, 2, 2),
        (3, 2, 2),
    ],
)
async def test_send_history(
    memory_backend: MemoryChannelsBackend,
    message_count: int,
    history_limit: int,
    chronological_order: bool,
    expected_history_count: int,
) -> None:
    memory_backend._max_history_length = 10
    plugin = ChannelsPlugin(
        backend=memory_backend,
        arbitrary_channels_allowed=True,
        send_history_chronological=chronological_order,
    )
    mock_handle_send = MockPluginHandleSocketSend()
    mock_socket = AsyncMock()
    plugin.handle_socket_send = mock_handle_send  # type: ignore[method-assign]

    await memory_backend.on_startup()
    messages = await _populate_channels_backend(message_count=message_count, channel="foo", backend=memory_backend)

    await plugin.subscribe(mock_socket, channels=["foo"])

    await plugin.send_history(
        socket=mock_socket, channels=["foo"], limit=history_limit, chronological=chronological_order
    )

    assert mock_handle_send.call_count == expected_history_count
    if expected_history_count:
        expected_messages = messages[-expected_history_count:]
        if not chronological_order:
            expected_messages = sorted(expected_messages)
        assert mock_handle_send.get_data_call_args(ordered=chronological_order) == expected_messages


@pytest.mark.parametrize("chronological_order", [True, False])
@pytest.mark.parametrize(
    "message_count,history,expected_history_count",
    [
        (2, -1, 2),
        (2, 1, 1),
        (2, 2, 2),
        (3, 2, 2),
        (2, 0, 0),
    ],
)
async def test_handler_sends_history(
    memory_backend: MemoryChannelsBackend,
    message_count: int,
    history: int,
    expected_history_count: int,
    chronological_order: bool,
) -> None:
    memory_backend._max_history_length = 10
    plugin = ChannelsPlugin(
        backend=memory_backend,
        arbitrary_channels_allowed=True,
        history=history,
        create_route_handlers=True,
        send_history_chronological=chronological_order,
    )

    mock_handle_send = MockPluginHandleSocketSend()
    plugin.handle_socket_send = mock_handle_send  # type: ignore[method-assign]

    app = Litestar([], plugins=[plugin])
    with TestClient(app) as client:
        await memory_backend.subscribe(["foo"])
        messages = await _populate_channels_backend(message_count=message_count, channel="foo", backend=memory_backend)

        with client.websocket_connect("/foo"):
            pass

    assert mock_handle_send.call_count == expected_history_count
    if expected_history_count:
        expected_messages = messages[-expected_history_count:]
        if not chronological_order:
            expected_messages = sorted(expected_messages)
        assert mock_handle_send.get_data_call_args(ordered=chronological_order) == expected_messages
