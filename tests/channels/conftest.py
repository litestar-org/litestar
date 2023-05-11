from __future__ import annotations

import pytest
from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.channels.backends.redis import RedisChannelsPubSubBackend, RedisChannelsStreamBackend


@pytest.fixture()
def redis_client(docker_ip: str) -> AsyncRedis:
    Redis(host=docker_ip, port=6397).flushall()
    return AsyncRedis(host=docker_ip, port=6397)


@pytest.fixture()
def redis_stream_backend(redis_client: AsyncRedis) -> RedisChannelsStreamBackend:
    return RedisChannelsStreamBackend(history=10, redis=redis_client, cap_streams_approximate=False)


@pytest.fixture()
def redis_pub_sub_backend(redis_client: AsyncRedis) -> RedisChannelsPubSubBackend:
    return RedisChannelsPubSubBackend(redis=redis_client)


@pytest.fixture()
def memory_backend() -> MemoryChannelsBackend:
    return MemoryChannelsBackend(history=10)
