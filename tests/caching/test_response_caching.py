from datetime import datetime, timedelta
from time import sleep

import pytest
from _pytest.fixtures import FixtureRequest
from fakeredis.aioredis import FakeRedis
from freezegun import freeze_time
from pytest_mock import MockerFixture

from starlite import CacheConfig, Request, get
from starlite.cache.base import CacheBackendProtocol
from starlite.cache.memcached_cache_backend import (
    MemcachedCacheBackend,
    MemcachedCacheBackendConfig,
)
from starlite.cache.redis_cache_backend import (
    RedisCacheBackend,
    RedisCacheBackendConfig,
)
from starlite.cache.simple_cache_backend import SimpleCacheBackend
from starlite.testing import create_test_client

from ..mocks import FakeAsyncMemcached
from . import after_request_handler, slow_handler


@pytest.fixture()
def fake_redis(mocker: MockerFixture) -> FakeRedis:
    redis = FakeRedis()
    mocker.patch("starlite.cache.redis_cache_backend.Redis")
    mocker.patch("starlite.cache.redis_cache_backend.RedisCacheBackend._redis", redis)

    return redis


@pytest.fixture
def redis_backend(fake_redis: FakeRedis) -> RedisCacheBackend:
    return RedisCacheBackend(config=RedisCacheBackendConfig(url="redis://something"))


@pytest.fixture()
def fake_memcached(mocker: MockerFixture) -> FakeAsyncMemcached:
    memcached = FakeAsyncMemcached()
    mocker.patch("starlite.cache.memcached_cache_backend.Client")
    mocker.patch("starlite.cache.memcached_cache_backend.MemcachedCacheBackend._memcached_client", memcached)

    return memcached


@pytest.fixture()
def memcached_backend(fake_memcached: FakeAsyncMemcached) -> MemcachedCacheBackend:
    return MemcachedCacheBackend(config=MemcachedCacheBackendConfig(host="localhost"))


@pytest.fixture()
def simple_cache_backend() -> SimpleCacheBackend:
    return SimpleCacheBackend()


@pytest.fixture(params=["redis_backend", "memcached_backend", "simple_cache_backend"])
def cache_backend(request: FixtureRequest) -> CacheBackendProtocol:
    return request.getfixturevalue(request.param)  # type: ignore[no-any-return]


@pytest.mark.parametrize("sync_to_thread", (True, False))
def test_default_cache_response(sync_to_thread: bool, cache_backend: CacheBackendProtocol) -> None:
    with create_test_client(
        route_handlers=[
            get(
                "/cached",
                sync_to_thread=sync_to_thread,
                cache=True,
                type_encoders={
                    int: str
                },  # test pickling issues. see https://github.com/starlite-api/starlite/issues/1096
            )(slow_handler)
        ],
        after_request=after_request_handler,
        cache_config=CacheConfig(backend=cache_backend),
    ) as client:
        first_response = client.get("/cached")
        assert first_response.status_code == 200

        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier

        second_response = client.get("/cached")

        assert second_response.status_code == 200
        assert second_response.headers["unique-identifier"] == first_response_identifier
        assert first_response.json() == second_response.json()


def test_handler_expiration(cache_backend: CacheBackendProtocol) -> None:
    now = datetime.now()
    with freeze_time(now) as frozen_datetime, create_test_client(
        route_handlers=[get("/cached-local", cache=10)(slow_handler)],
        after_request=after_request_handler,
        cache_config=CacheConfig(backend=cache_backend),
    ) as client:
        first_response = client.get("/cached-local")
        frozen_datetime.tick(delta=timedelta(seconds=5))
        second_response = client.get("/cached-local")
        assert first_response.headers["unique-identifier"] == second_response.headers["unique-identifier"]
        frozen_datetime.tick(delta=timedelta(seconds=11))
        third_response = client.get("/cached-local")
        assert first_response.headers["unique-identifier"] != third_response.headers["unique-identifier"]


def test_default_expiration(cache_backend: CacheBackendProtocol) -> None:
    with create_test_client(
        route_handlers=[get("/cached-default", cache=True)(slow_handler)],
        after_request=after_request_handler,
        cache_config=CacheConfig(expiration=1),
    ) as client:
        first_response = client.get("/cached-default")
        second_response = client.get("/cached-default")
        assert first_response.headers["unique-identifier"] == second_response.headers["unique-identifier"]
        sleep(1.2)
        third_response = client.get("/cached-default")
        assert first_response.headers["unique-identifier"] != third_response.headers["unique-identifier"]


@pytest.mark.parametrize("sync_to_thread", (True, False))
async def test_custom_cache_key(sync_to_thread: bool, anyio_backend: str) -> None:
    def custom_cache_key_builder(request: Request) -> str:
        return request.url.path + ":::cached"

    with create_test_client(
        route_handlers=[
            get("/cached", sync_to_thread=sync_to_thread, cache=True, cache_key_builder=custom_cache_key_builder)(
                slow_handler
            )
        ]
    ) as client:
        client.get("/cached")
        value = await client.app.cache.get("/cached:::cached")
        assert value
