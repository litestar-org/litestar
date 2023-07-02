#
#
#
#
#
#
# @pytest.fixture(
# def channels_backend(request: FixtureRequest) -> ChannelsBackend:
#
#
# def test_channels_no_channels_arbitrary_not_allowed_raises(memory_backend: MemoryChannelsBackend) -> None:
#     with pytest.raises(ImproperlyConfiguredException):
#
#
# def test_broadcast_not_initialized_raises(memory_backend: MemoryChannelsBackend) -> None:
#     with pytest.raises(RuntimeError):
#
#
# def test_plugin_dependency(mock: MagicMock, memory_backend: MemoryChannelsBackend) -> None:
#     @get()
#     def handler(channels: ChannelsPlugin) -> None:
#
#
#     with create_test_client(handler, plugins=[channels_plugin]) as client:
#
#
#
# def test_plugin_dependency_signature_namespace(memory_backend: MemoryChannelsBackend) -> None:
#
#
# @pytest.mark.flaky(reruns=5)
# async def test_pub_sub_wait_published(channels_backend: ChannelsBackend) -> None:
#     async with ChannelsPlugin(backend=channels_backend, channels=["something"]) as plugin:
#
#
#
#
# @pytest.mark.flaky(reruns=5)
# async def test_pub_sub_non_blocking(channels_backend: ChannelsBackend) -> None:
#     async with ChannelsPlugin(backend=channels_backend, channels=["something"]) as plugin:
#
#
#
#
#
# @pytest.mark.flaky(reruns=5)
# async def test_pub_sub_run_in_background(channels_backend: ChannelsBackend, async_mock: AsyncMock) -> None:
#     async with ChannelsPlugin(backend=channels_backend, channels=["something"]) as plugin:
#         async with subscriber.run_in_background(async_mock):
#
#
#
# @pytest.mark.flaky(reruns=5)
# @pytest.mark.parametrize("socket_send_mode", ["text", "binary"])
# @pytest.mark.parametrize("handler_base_path", [None, "/ws"])
# def test_create_ws_route_handlers(
#     channels_backend: ChannelsBackend, handler_base_path: str | None, socket_send_mode: WebSocketMode
# ) -> None:
#
#     with TestClient(app) as client, client.websocket_connect(f"{handler_base_path or ''}/something") as ws:
#
#
# @pytest.mark.flaky(reruns=5)
# async def test_create_ws_route_handlers_arbitrary_channels_allowed(channels_backend: ChannelsBackend) -> None:
#
#
#     with TestClient(app) as client:
#         with client.websocket_connect("/ws/foo") as ws:
#
#         with client.websocket_connect("/ws/bar") as ws:
#
#
# @pytest.mark.parametrize("arbitrary_channels_allowed", [True, False])
# @pytest.mark.parametrize("channels", ["foo", ["foo", "bar"]])
# async def test_subscribe(
#     async_mock: AsyncMock,
#     memory_backend: MemoryChannelsBackend,
#     channels: str | list[str],
#     arbitrary_channels_allowed: bool,
# ) -> None:
#
#
#     if isinstance(channels, str):
#
#     for channel in channels:
#
#
#
# @pytest.mark.parametrize("arbitrary_channels_allowed", [True, False])
# @pytest.mark.parametrize("channels", ["foo", ["foo", "bar"]])
# async def test_start_subscription(
#     async_mock: AsyncMock,
#     memory_backend: MemoryChannelsBackend,
#     channels: str | list[str],
#     arbitrary_channels_allowed: bool,
# ) -> None:
#
#     async with plugin.start_subscription(channels) as subscriber:
#         if isinstance(channels, str):
#
#         for channel in channels:
#
#
#
#
# @pytest.mark.parametrize("history", [1, 2])
# @pytest.mark.parametrize("channels", [["foo"], ["foo", "bar"]])
# async def test_subscribe_with_history(
#     async_mock: AsyncMock, memory_backend: MemoryChannelsBackend, channels: list[str], history: int
# ) -> None:
#     async with ChannelsPlugin(backend=memory_backend, channels=channels) as plugin:
#
#         for channel in channels:
#
#
#
#
# @pytest.mark.flaky(reruns=5)
# @pytest.mark.parametrize("history", [1, 2])
# @pytest.mark.parametrize("channels", [["foo"], ["foo", "bar"]])
# async def test_start_subscription_with_history(
#     async_mock: AsyncMock, memory_backend: MemoryChannelsBackend, channels: list[str], history: int
# ) -> None:
#     async with ChannelsPlugin(backend=memory_backend, channels=channels) as plugin:
#
#         for channel in channels:
#
#         async with plugin.start_subscription(channels, history=history) as subscriber:
#
#
# async def test_subscribe_non_existent_channel_raises(memory_backend: MemoryChannelsBackend) -> None:
#
#     with pytest.raises(LitestarException):
#
#
# @pytest.mark.parametrize("unsubscribe_all", [False, True])
# @pytest.mark.parametrize("channels", ["foo", ["foo", "bar"]])
# async def test_unsubscribe(
#     async_mock: AsyncMock, memory_backend: MemoryChannelsBackend, channels: str | list[str], unsubscribe_all: bool
# ) -> None:
#
#
#     if isinstance(channels, str):
#
#
#     for channel in channels:
#         assert channel in plugin._channels
#
#
# async def test_subscribe_after_unsubscribe(memory_backend: MemoryChannelsBackend) -> None:
#
#
#
# async def test_unsubscribe_last_subscriber_unsubscribes_backend(
#     memory_backend: MemoryChannelsBackend, async_mock: AsyncMock
# ) -> None:
#
#
#
#
#
# async def _populate_channels_backend(*, message_count: int, channel: str, backend: ChannelsBackend) -> list[bytes]:
#
#     for message in messages:
#
#
# @pytest.mark.parametrize(
#     "message_count,handler_send_history,expected_history_count",
#     ],
# async def test_handler_sends_history(
#     memory_backend: MemoryChannelsBackend,
#     message_count: int,
#     handler_send_history: int,
#     expected_history_count: int,
#     mocker: MockerFixture,
# ) -> None:
#
#     with TestClient(app) as client:
#
#         with client.websocket_connect("/foo"):
#             pass
#
#     if expected_history_count:
#
#
# @pytest.mark.parametrize("channels,expected_entry_count", [("foo", 1), (["foo", "bar"], 2)])
# async def test_set_subscriber_history(
#     channels: str | list[str], memory_backend: MemoryChannelsBackend, expected_entry_count: int
# ) -> None:
#     async with ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True) as plugin:
#
#
#
#
# @pytest.mark.parametrize("backlog_strategy", ["backoff", "dropleft"])
# async def test_backlog(
#     memory_backend: MemoryChannelsBackend, backlog_strategy: BacklogStrategy, async_mock: AsyncMock
# ) -> None:
#
#     async with plugin:
#         async with subscriber.run_in_background(async_mock):
#             for message in messages:
#
#
