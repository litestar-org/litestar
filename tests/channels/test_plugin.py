from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.fixtures import FixtureRequest
from pytest_mock import MockerFixture

from litestar import Litestar, get
from litestar.channels import ChannelsBackend, ChannelsPlugin
from litestar.channels.memory import MemoryChannelsBackend
from litestar.channels.plugin import BacklogStrategy
from litestar.exceptions import ImproperlyConfiguredException, LitestarException
from litestar.testing import TestClient, create_test_client
from litestar.types.asgi_types import WebSocketMode
from litestar.utils.compat import async_next

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


def test_broadcast_not_initialized_raises(memory_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)
    with pytest.raises(RuntimeError):
        plugin.publish("foo", "bar")


async def test_pub_sub(channels_backend: ChannelsBackend) -> None:
    async with ChannelsPlugin(backend=channels_backend, channels=["something"]) as plugin:
        subscriber = await plugin.subscribe("something")
        stream = subscriber.iter_events()
        await plugin.wait_published(b"foo", "something")

        res = await asyncio.wait_for(async_next(stream), timeout=1)

    assert res == b"foo"


async def test_pub_sub_non_blocking(channels_backend: ChannelsBackend) -> None:
    async with ChannelsPlugin(backend=channels_backend, channels=["something"]) as plugin:
        subscriber = await plugin.subscribe("something")
        stream = subscriber.iter_events()
        plugin.publish(b"foo", "something")

        res = await asyncio.wait_for(async_next(stream), timeout=1)

    assert res == b"foo"


async def test_pub_sub_run_in_background(channels_backend: ChannelsBackend, async_mock: AsyncMock) -> None:
    async with ChannelsPlugin(backend=channels_backend, channels=["something"]) as plugin:
        subscriber = await plugin.subscribe("something")
        async with subscriber.run_in_background(async_mock):
            plugin.publish(b"foo", "something")
            await asyncio.sleep(0.1)

    assert async_mock.call_count == 1


@pytest.mark.parametrize("socket_send_mode", ["text", "binary"])
@pytest.mark.parametrize("handler_base_path", [None, "/ws"])
def test_pub_sub_create_route_handlers(
    channels_backend: ChannelsBackend, handler_base_path: str | None, socket_send_mode: WebSocketMode
) -> None:
    channels_plugin = ChannelsPlugin(
        backend=channels_backend,
        create_ws_route_handlers=True,
        channels=["something"],
        ws_handler_base_path=handler_base_path or "/",
        ws_send_mode=socket_send_mode,
    )
    app = Litestar(plugins=[channels_plugin])

    with TestClient(app) as client, client.websocket_connect(f"{handler_base_path or ''}/something") as ws:
        channels_plugin.publish(["foo"], "something")
        assert ws.receive_json(mode=socket_send_mode, timeout=0.1) == ["foo"]


async def test_create_route_handlers_arbitrary_channels_allowed(channels_backend: ChannelsBackend) -> None:
    channels_plugin = ChannelsPlugin(
        backend=channels_backend,
        arbitrary_channels_allowed=True,
        create_ws_route_handlers=True,
        ws_handler_base_path="/ws",
    )

    app = Litestar(plugins=[channels_plugin])

    with TestClient(app) as client:
        with client.websocket_connect("/ws/foo") as ws:
            channels_plugin.publish("something", "foo")
            assert ws.receive_text(timeout=1) == "something"

        with client.websocket_connect("/ws/bar") as ws:
            channels_plugin.publish("something else", "bar")
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
    MagicMock()

    subscriber = await plugin.subscribe(channels)

    if isinstance(channels, str):
        channels = [channels]

    for channel in channels:
        assert subscriber in plugin._channels[channel]

    async_mock.assert_called_once_with(set(channels))


async def test_subscribe_non_existent_channel_raises(memory_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, channels=["foo"])

    with pytest.raises(LitestarException):
        await plugin.subscribe("bar")


@pytest.mark.parametrize("unsubscribe_all", [False, True])
@pytest.mark.parametrize("channels", ["foo", ["foo", "bar"]])
async def test_unsubscribe(
    async_mock: AsyncMock, memory_backend: MemoryChannelsBackend, channels: str | list[str], unsubscribe_all: bool
) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, channels=["foo", "bar"])
    memory_backend.unsubscribe = async_mock  # type: ignore[method-assign]
    subscriber_1 = await plugin.subscribe(channels=channels)
    subscriber_2 = await plugin.subscribe(channels=channels)

    await plugin.unsubscribe(subscriber_1, channels=channels if not unsubscribe_all else None)

    if isinstance(channels, str):
        channels = [channels]

    assert async_mock.call_count == 0

    for channel in channels:
        assert subscriber_2 in plugin._channels[channel]


async def test_unsubscribe_last_subscriber_unsubscribes_backend(
    memory_backend: MemoryChannelsBackend, async_mock: AsyncMock
) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, channels=["foo"])
    memory_backend.unsubscribe = async_mock  # type: ignore[method-assign]
    subscriber_1 = await plugin.subscribe(channels="foo")
    subscriber_2 = await plugin.subscribe(channels="foo")

    await plugin.unsubscribe(subscriber=subscriber_1, channels="foo")
    await plugin.unsubscribe(subscriber=subscriber_2, channels="foo")

    assert async_mock.call_count == 1

    assert not plugin._channels.get("foo")


async def _populate_channels_backend(*, message_count: int, channel: str, backend: ChannelsBackend) -> list[bytes]:
    messages = [f"message {i}".encode() for i in range(message_count)]

    for message in messages:
        await backend.publish(message, [channel])
    await backend.publish(b"some other message", ["bar"])
    return messages


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
    expected_history_count: int,
    async_mock: AsyncMock,
) -> None:
    memory_backend._max_history_length = 10
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)

    await memory_backend.on_startup()
    messages = await _populate_channels_backend(message_count=message_count, channel="foo", backend=memory_backend)

    subscriber = await plugin.subscribe(channels=["foo"])
    async with subscriber.run_in_background(async_mock):
        await subscriber.put_history(channels=["foo"], limit=history_limit)

    assert async_mock.call_count == expected_history_count
    if expected_history_count:
        expected_messages = messages[-expected_history_count:]
        assert [call.args[0] for call in async_mock.call_args_list] == expected_messages

    await plugin._on_shutdown()


@pytest.mark.parametrize(
    "message_count,handler_send_history,expected_history_count",
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
    handler_send_history: int,
    expected_history_count: int,
    mocker: MockerFixture,
) -> None:
    mock_socket_send = mocker.patch("litestar.connection.websocket.WebSocket.send_data")
    memory_backend._max_history_length = 10
    plugin = ChannelsPlugin(
        backend=memory_backend,
        arbitrary_channels_allowed=True,
        ws_handler_send_history=handler_send_history,
        create_ws_route_handlers=True,
    )

    app = Litestar([], plugins=[plugin])
    with TestClient(app) as client:
        await memory_backend.subscribe(["foo"])
        messages = await _populate_channels_backend(message_count=message_count, channel="foo", backend=memory_backend)

        with client.websocket_connect("/foo"):
            pass

    assert mock_socket_send.call_count == expected_history_count
    if expected_history_count:
        expected_messages = messages[-expected_history_count:]
        assert [call.kwargs.get("data") for call in mock_socket_send.call_args_list] == expected_messages


@pytest.mark.parametrize("backlog_strategy", ["backoff", "dropleft"])
async def test_backlog(
    memory_backend: MemoryChannelsBackend, backlog_strategy: BacklogStrategy, async_mock: AsyncMock
) -> None:
    plugin = ChannelsPlugin(
        backend=memory_backend,
        arbitrary_channels_allowed=True,
        subscriber_max_backlog=2,
        subscriber_backlog_strategy=backlog_strategy,
    )
    messages = [b"foo", b"bar", b"baz"]

    await plugin._on_startup()

    subscriber = await plugin.subscribe(channels=["something"])

    async with subscriber.run_in_background(async_mock):
        for message in messages:
            await plugin.wait_published(message, channels=["something"])

        await plugin._on_shutdown()

    expected_messages = messages[:-1] if backlog_strategy == "backoff" else messages[1:]

    assert async_mock.call_count == 2
    assert [call.args[0] for call in async_mock.call_args_list] == expected_messages
