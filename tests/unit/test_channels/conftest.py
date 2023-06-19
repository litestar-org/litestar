from __future__ import annotations

from typing import AsyncGenerator

import pytest
from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.channels.backends.redis import RedisChannelsPubSubBackend, RedisChannelsStreamBackend


@pytest.fixture()
async def redis_client(docker_ip: str) -> AsyncGenerator[AsyncRedis, None]:
    # this is to get around some weirdness with pytest-asyncio and redis interaction
    # on 3.8 and 3.9

    Redis(host=docker_ip, port=6397).flushall()
    client: AsyncRedis = AsyncRedis(host=docker_ip, port=6397)
    yield client
    try:
        await client.close()
    except RuntimeError:
        pass


@pytest.fixture()
def redis_stream_backend(redis_client: AsyncRedis) -> RedisChannelsStreamBackend:
    return RedisChannelsStreamBackend(history=10, redis=redis_client, cap_streams_approximate=False)


@pytest.fixture()
def redis_pub_sub_backend(redis_client: AsyncRedis) -> RedisChannelsPubSubBackend:
    return RedisChannelsPubSubBackend(redis=redis_client)


@pytest.fixture()
def memory_backend() -> MemoryChannelsBackend:
    return MemoryChannelsBackend(history=10)
