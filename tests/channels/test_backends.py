from typing import cast

import pytest
from _pytest.fixtures import FixtureRequest

from litestar.channels import ChannelsBackend
from litestar.channels.memory import MemoryChannelsBackend


@pytest.fixture(params=[pytest.param(MemoryChannelsBackend, id="memory")])
async def channels_backend_instance(request: FixtureRequest) -> ChannelsBackend:
    backend_class = cast(type[ChannelsBackend], request.param)
    return backend_class()


@pytest.fixture()
async def channels_backend(channels_backend_instance: ChannelsBackend) -> None:
    await channels_backend_instance.on_startup()
    yield channels_backend_instance
    await channels_backend_instance.on_shutdown()


@pytest.mark.parametrize("channels", [{"foo"}, {"foo", "bar"}])
async def test_pub_sub(channels_backend: ChannelsBackend, channels: set[str]) -> None:
    await channels_backend.publish("something", channels)

    event_generator = channels_backend.received_events()
    event = await anext(event_generator)
    assert event == ("something", channels)
