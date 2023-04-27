import asyncio
from asyncio import AbstractEventLoop, get_event_loop_policy
from pathlib import Path
from typing import Iterator

import pytest
from pytest_docker.plugin import Services
from redis.asyncio import Redis

from litestar.channels.memory import MemoryChannelsBackend
from litestar.channels.redis import RedisChannelsPubSubBackend, RedisChannelsStreamBackend


@pytest.fixture(scope="session")
def docker_compose_file() -> Path:
    """
    Returns:
        Path to the docker-compose file for end-to-end test environment.
    """
    return Path(__file__).parent / "docker-compose.yml"


@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    """Need the event loop scoped to the session so that we can use it to check
    containers are ready in session scoped containers fixture."""
    policy = get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def redis_service(docker_ip: str, docker_services: Services) -> Redis:
    redis_port = docker_services.port_for("redis", 6379)
    redis: Redis = Redis(host=docker_ip, port=redis_port)

    async def ping() -> None:
        for _ in range(10):
            if await redis.ping():
                break
            await asyncio.sleep(0.1)

    await asyncio.wait_for(ping(), timeout=10)

    return redis


@pytest.fixture()
async def redis_client(redis_service: Redis) -> Redis:
    await redis_service.flushall()
    return redis_service


@pytest.fixture()
async def redis_stream_backend(redis_client: Redis) -> RedisChannelsStreamBackend:
    return RedisChannelsStreamBackend(history=10, redis=redis_client, cap_streams_approximate=False)


@pytest.fixture()
def redis_pub_sub_backend(redis_client: Redis) -> RedisChannelsPubSubBackend:
    return RedisChannelsPubSubBackend(history=10, redis=redis_client)


@pytest.fixture()
def memory_backend() -> MemoryChannelsBackend:
    return MemoryChannelsBackend(history=10)
