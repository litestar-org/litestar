from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.fixtures import FixtureRequest

from litestar import Litestar, WebSocket, get, websocket
from litestar.channels import ChannelsBackend, ChannelsPlugin
from litestar.channels.memory import MemoryChannelsBackend
from litestar.exceptions import ImproperlyConfiguredException, LitestarException
from litestar.testing import TestClient, create_test_client


@pytest.fixture
def mock() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def async_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def memory_channels_backend() -> MemoryChannelsBackend:
    return MemoryChannelsBackend()


@pytest.fixture(params=[pytest.param("memory_channels_backend", id="memory")])
def channels_backend(request: FixtureRequest) -> ChannelsBackend:
    return cast(ChannelsBackend, request.getfixturevalue(request.param))


def test_channels_no_channels_arbitrary_not_allowed_raises(memory_channels_backend: MemoryChannelsBackend) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ChannelsPlugin(backend=memory_channels_backend)


def test_pub_sub(channels_backend: MemoryChannelsBackend) -> None:
    @websocket("/")
    async def handler(socket: WebSocket, channels: ChannelsPlugin) -> None:
        await socket.accept()
        await channels.subscribe(socket, "something")
        while True:
            await socket.receive()

    channels_plugin = ChannelsPlugin(backend=channels_backend, channels=["something"])
    app = Litestar([handler], plugins=[channels_plugin])

    with TestClient(app) as client, client.websocket_connect("/") as ws:
        channels_plugin.broadcast("foo", "something")
        assert ws.receive_json() == "foo"


@pytest.mark.parametrize("handler_base_path", [None, "/ws"])
def test_pub_sub_create_route_handlers(channels_backend: ChannelsBackend, handler_base_path: str | None) -> None:
    channels_plugin = ChannelsPlugin(
        backend=channels_backend,
        create_route_handlers=True,
        channels=["something"],
        handler_base_path=handler_base_path or "/",
    )
    app = Litestar(plugins=[channels_plugin])

    with TestClient(app) as client, client.websocket_connect(f"{handler_base_path or ''}/something") as ws:
        channels_plugin.broadcast("foo", "something")
        assert ws.receive_json() == "foo"


def test_create_route_handlers_arbitrary_channels_allowed(channels_backend: ChannelsBackend) -> None:
    channels_plugin = ChannelsPlugin(
        backend=channels_backend, arbitrary_channels_allowed=True, create_route_handlers=True, handler_base_path="/ws"
    )

    app = Litestar(plugins=[channels_plugin])

    with TestClient(app) as client:
        with client.websocket_connect("/ws/foo") as ws:
            channels_plugin.broadcast("something", "foo")
            assert ws.receive_json() == "something"

        with client.websocket_connect("/ws/bar") as ws:
            channels_plugin.broadcast("something else", "bar")
            assert ws.receive_json() == "something else"


def test_plugin_dependency(mock: MagicMock, memory_channels_backend: MemoryChannelsBackend) -> None:
    @get()
    def handler(channels: ChannelsPlugin) -> None:
        mock(channels)

    channels_plugin = ChannelsPlugin(backend=memory_channels_backend, arbitrary_channels_allowed=True)

    with create_test_client(handler, plugins=[channels_plugin]) as client:
        res = client.get("/")
        assert res.status_code == 200

    assert mock.call_count == 1
    assert mock.call_args[0][0] is channels_plugin


@pytest.mark.parametrize("arbitrary_channels_allowed", [True, False])
@pytest.mark.parametrize("channels", ["foo", ["foo", "bar"]])
async def test_subscribe(
    async_mock: AsyncMock,
    memory_channels_backend: MemoryChannelsBackend,
    channels: str | list[str],
    arbitrary_channels_allowed: bool,
) -> None:
    plugin = ChannelsPlugin(
        backend=memory_channels_backend,
        channels=["foo", "bar"] if not arbitrary_channels_allowed else None,
        arbitrary_channels_allowed=arbitrary_channels_allowed,
    )
    memory_channels_backend.subscribe = async_mock
    socket = object()

    await plugin.subscribe(socket=socket, channels=channels)

    if isinstance(channels, str):
        channels = [channels]

    for channel in channels:
        subscribers = plugin._channels.get(channel)
        assert subscribers
        assert socket in subscribers

    async_mock.assert_called_once_with(set(channels))


async def test_subscribe_non_existent_channel_raises(memory_channels_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_channels_backend, channels=["foo"])

    with pytest.raises(LitestarException):
        await plugin.subscribe(object(), "bar")


@pytest.mark.parametrize("channels", ["foo", ["foo", "bar"]])
async def test_unsubscribe(
    async_mock: AsyncMock,
    memory_channels_backend: MemoryChannelsBackend,
    channels: str | list[str],
) -> None:
    plugin = ChannelsPlugin(backend=memory_channels_backend, channels=["foo", "bar"])
    memory_channels_backend.unsubscribe = async_mock
    socket_1 = object()
    socket_2 = object()
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
    memory_channels_backend: MemoryChannelsBackend, async_mock: AsyncMock
) -> None:
    plugin = ChannelsPlugin(backend=memory_channels_backend, channels=["foo"])
    memory_channels_backend.unsubscribe = async_mock
    socket_1 = object()
    socket_2 = object()
    await plugin.subscribe(socket=socket_1, channels="foo")
    await plugin.subscribe(socket=socket_2, channels="foo")

    await plugin.unsubscribe(socket=socket_1, channels="foo")
    await plugin.unsubscribe(socket=socket_2, channels="foo")

    assert async_mock.call_count == 1

    assert not plugin._channels.get("foo")
