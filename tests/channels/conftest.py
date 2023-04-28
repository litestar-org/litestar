from __future__ import annotations

import asyncio
import timeit
from asyncio import AbstractEventLoop, get_event_loop_policy
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterator

import pytest
from pytest_docker.plugin import Services
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError as RedisConnectionError

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


async def wait_until_responsive(
    check: Callable[..., Awaitable],
    timeout: float,
    pause: float,
    **kwargs: Any,
) -> None:
    """Wait until a service is responsive.

    Args:
        check: Coroutine, return truthy value when waiting should stop.
        timeout: Maximum seconds to wait.
        pause: Seconds to wait between calls to `check`.
        **kwargs: Given as kwargs to `check`.
    """
    ref = timeit.default_timer()
    now = ref
    while (now - ref) < timeout:
        if await check(**kwargs):
            return
        await asyncio.sleep(pause)
        now = timeit.default_timer()

    raise Exception("Timeout reached while waiting on service!")


async def redis_responsive(host: str) -> bool:
    """Args:
        host: docker IP address.

    Returns:
        Boolean indicating if we can connect to the redis server.
    """
    client: AsyncRedis = AsyncRedis(host=host, port=6397)
    try:
        return await client.ping()
    except (ConnectionError, RedisConnectionError):
        return False
    finally:
        await client.close()


@pytest.fixture(scope="session", autouse=True)
async def _containers(docker_ip: str, docker_services: Services) -> None:  # pylint: disable=unused-argument
    """Starts containers for required services, fixture waits until they are
    responsive before returning.

    Args:
        docker_ip: the test docker IP
        docker_services: the test docker services
    """
    await wait_until_responsive(timeout=30.0, pause=0.1, check=redis_responsive, host=docker_ip)


@pytest.fixture()
def redis_client(docker_ip: str, docker_services: Services) -> AsyncRedis:
    Redis(host=docker_ip, port=6397).flushall()
    return AsyncRedis(host=docker_ip, port=6397)


@pytest.fixture()
def redis_stream_backend(redis_client: AsyncRedis) -> RedisChannelsStreamBackend:
    return RedisChannelsStreamBackend(history=10, redis=redis_client, cap_streams_approximate=False)


@pytest.fixture()
def redis_pub_sub_backend(redis_client: AsyncRedis) -> RedisChannelsPubSubBackend:
    return RedisChannelsPubSubBackend(history=10, redis=redis_client)


@pytest.fixture()
def memory_backend() -> MemoryChannelsBackend:
    return MemoryChannelsBackend(history=10)
