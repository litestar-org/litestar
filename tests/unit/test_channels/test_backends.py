#
#
#
#
#
# @pytest.fixture(
# def channels_backend_instance(request: FixtureRequest) -> ChannelsBackend:
#
#
# @pytest.fixture()
# async def channels_backend(channels_backend_instance: ChannelsBackend) -> AsyncGenerator[ChannelsBackend, None]:
#     yield channels_backend_instance
#
#
# @pytest.mark.parametrize("channels", [{"foo"}, {"foo", "bar"}])
# async def test_pub_sub(channels_backend: ChannelsBackend, channels: set[str]) -> None:
#
#     for _ in channels:
#
#
# async def test_pub_sub_no_subscriptions(channels_backend: ChannelsBackend) -> None:
#
#     with pytest.raises((asyncio.TimeoutError, TimeoutError)):
#
#
# async def test_pub_sub_no_subscriptions_by_unsubscribes(channels_backend: ChannelsBackend) -> None:
#
#
#     with pytest.raises((asyncio.TimeoutError, TimeoutError)):
#
#
# async def test_pub_sub_shutdown_leftover_messages(channels_backend_instance: ChannelsBackend) -> None:
#
#
#
#
# @pytest.mark.parametrize("history_limit,expected_history_length", [(None, 10), (1, 1), (5, 5), (10, 10)])
# async def test_get_history(
#     channels_backend: ChannelsBackend, history_limit: int | None, expected_history_length: int
# ) -> None:
#     if isinstance(channels_backend, RedisChannelsPubSubBackend):
#
#     for message in messages:
#
#
#
#
# async def test_discards_history_entries(channels_backend: ChannelsBackend) -> None:
#     if isinstance(channels_backend, RedisChannelsPubSubBackend):
#
#     for _ in range(20):
#
#
#
# async def test_redis_streams_backend_flushall(redis_stream_backend: RedisChannelsStreamBackend) -> None:
#
#
#
#
# @pytest.mark.flaky(reruns=5)  # this should not really happen but just in case, we retry
# async def test_redis_stream_backend_expires(redis_client: Redis) -> None:
#
#
#
#
# async def test_memory_publish_not_initialized_raises() -> None:
#
#     with pytest.raises(RuntimeError):
