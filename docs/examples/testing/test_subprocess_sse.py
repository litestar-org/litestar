"""
Test the app running in a subprocess
"""

import asyncio
import pathlib
import sys
from typing import AsyncIterator

import httpx
import httpx_sse
import pytest
from redis.asyncio import Redis

from litestar.channels import ChannelsPlugin
from litestar.channels.backends.redis import RedisChannelsPubSubBackend
from litestar.testing import subprocess_async_client

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


ROOT = pathlib.Path(__file__).parent


@pytest.fixture(name="async_client", scope="session")
async def fx_async_client() -> AsyncIterator[httpx.AsyncClient]:
    async with subprocess_async_client(workdir=ROOT, app="subprocess_sse_app:app") as client:
        yield client


@pytest.fixture(name="redis_channels")
async def fx_redis_channels() -> AsyncIterator[ChannelsPlugin]:
    # Expects separate redis set-up
    redis_instance = Redis()
    channels_backend = RedisChannelsPubSubBackend(redis=redis_instance)
    channels_instance = ChannelsPlugin(backend=channels_backend, arbitrary_channels_allowed=True)
    await channels_instance._on_startup()
    yield channels_instance
    await channels_instance._on_shutdown()


async def test_subprocess_async_client(async_client: httpx.AsyncClient, redis_channels: ChannelsPlugin) -> None:
    """Demonstrates functionality of the async client with an infinite SSE source that cannot be tested with the
    regular async test client.
    """
    topic = "demo"
    message = "hello"

    running = asyncio.Event()
    running.set()

    async def send_notifications() -> None:
        while running.is_set():
            await redis_channels.wait_published(message, channels=[topic])
            await asyncio.sleep(0.1)

    task = asyncio.create_task(send_notifications())

    async with httpx_sse.aconnect_sse(async_client, "GET", f"/notify/{topic}") as event_source:
        async for event in event_source.aiter_sse():
            assert event.data == message
            running.clear()
            break
    await task
