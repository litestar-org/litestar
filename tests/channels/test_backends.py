import asyncio
from typing import AsyncGenerator, cast

import pytest
from _pytest.fixtures import FixtureRequest

from litestar.channels import ChannelsBackend
from litestar.channels.memory import MemoryChannelsBackend


@pytest.fixture(params=[pytest.param(MemoryChannelsBackend, id="memory")])
async def channels_backend_instance(request: FixtureRequest) -> ChannelsBackend:
    backend = cast(type[ChannelsBackend], request.param)
    return backend(history=10)


@pytest.fixture()
async def channels_backend(channels_backend_instance: ChannelsBackend) -> AsyncGenerator[ChannelsBackend, None]:
    await channels_backend_instance.on_startup()
    yield channels_backend_instance
    await channels_backend_instance.on_shutdown()


@pytest.mark.parametrize("channels", [{"foo"}, {"foo", "bar"}])
async def test_pub_sub(channels_backend: ChannelsBackend, channels: set[str]) -> None:
    await channels_backend.publish(b"something", channels)

    event_generator = channels_backend.stream_events()
    received = set()
    for _ in channels:
        received.add(await anext(event_generator))
    assert received == {(c, b"something") for c in channels}


async def test_pub_sub_shutdown_leftover_messages(channels_backend_instance: ChannelsBackend) -> None:
    await channels_backend_instance.on_startup()

    await channels_backend_instance.publish(b"something", {"foo"})

    await asyncio.wait_for(channels_backend_instance.on_shutdown(), timeout=0.1)


@pytest.mark.parametrize("history_limit,expected_history_length", [(None, 10), (1, 1), (5, 5), (10, 10)])
async def test_get_history(
    channels_backend: ChannelsBackend, history_limit: int | None, expected_history_length: int
) -> None:
    messages = [str(i).encode() for i in range(100)]
    for message in messages:
        await channels_backend.publish(message, {"something"})

    history = await channels_backend.get_history("something", history_limit)

    expected_messages = messages[-expected_history_length:]
    assert len(history) == expected_history_length
    assert history == expected_messages


async def test_memory_backend_discards_history_entries(channels_backend: ChannelsBackend) -> None:
    for _ in range(20):
        await channels_backend.publish(b"foo", {"bar"})

    assert len(await channels_backend.get_history("bar")) == 10
