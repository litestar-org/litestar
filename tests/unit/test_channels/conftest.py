from __future__ import annotations

import pytest
from redis.asyncio import Redis as AsyncRedis

from litestar.channels.backends.asyncpg import AsyncPgChannelsBackend
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.channels.backends.psycopg import PsycoPgChannelsBackend
from litestar.channels.backends.redis import RedisChannelsPubSubBackend, RedisChannelsStreamBackend


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Adds a timeout marker of 30 seconds to all test items in the 'tests/unit/test_channels'
    module and its submodules.
    """

    # This is an interim measure to diagnose stuck tests
    # Should be removed once the problem has been identified
    # Below are a few examples that displayed this behavior
    # https://github.com/litestar-org/litestar/actions/runs/5629765460/job/15255093668
    # https://github.com/litestar-org/litestar/actions/runs/5647890525/job/15298927200

    test_module_path = config.rootpath / "tests/unit/test_channels"
    for item in items:
        if test_module_path in item.path.parents:
            item.add_marker(pytest.mark.timeout(30))


@pytest.fixture()
def redis_stream_backend(redis_client: AsyncRedis) -> RedisChannelsStreamBackend:
    return RedisChannelsStreamBackend(redis=redis_client, cap_streams_approximate=False, history=1)


@pytest.fixture()
def redis_stream_backend_with_history(redis_client: AsyncRedis) -> RedisChannelsStreamBackend:
    return RedisChannelsStreamBackend(redis=redis_client, cap_streams_approximate=False, history=10)


@pytest.fixture()
def redis_pub_sub_backend(redis_client: AsyncRedis) -> RedisChannelsPubSubBackend:
    return RedisChannelsPubSubBackend(redis=redis_client)


@pytest.fixture()
def memory_backend() -> MemoryChannelsBackend:
    return MemoryChannelsBackend()


@pytest.fixture()
def memory_backend_with_history() -> MemoryChannelsBackend:
    return MemoryChannelsBackend(history=10)


@pytest.fixture()
def postgres_asyncpg_backend(postgres_service: None, docker_ip: str) -> AsyncPgChannelsBackend:
    return AsyncPgChannelsBackend(f"postgres://postgres:super-secret@{docker_ip}:5423")


@pytest.fixture()
def postgres_psycopg_backend(postgres_service: None, docker_ip: str) -> PsycoPgChannelsBackend:
    return PsycoPgChannelsBackend(f"postgres://postgres:super-secret@{docker_ip}:5423")
