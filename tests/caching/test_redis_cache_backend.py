from typing import Optional
from unittest.mock import patch, Mock
from starlite.cache.redis_cache_backend import RedisCacheBackend, RedisCacheBackendConfig


class FakeAsyncRedis:
    def __init__(self):
        self._cache = dict()
        self._expirations = dict()

    async def get(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        self._cache[key] = value
        self._expirations[key] = ex

    async def delete(self, key: str) -> None:
        self._cache.pop(key)

    def ttl(self, key: str) -> Optional[int]:
        return self._expirations.get(key)


@patch("starlite.cache.redis_cache_backend.ConnectionPool.from_url")
@patch("starlite.cache.redis_cache_backend.Redis")
def test_config_redis_default(_redis_mock: Mock, connection_pool_from_url_mock: Mock) -> None:
    url = "redis://localhost"
    config = RedisCacheBackendConfig(url=url)
    cache = RedisCacheBackend(config)
    assert cache._redis
    connection_pool_from_url_mock.assert_called_once_with(url=url)


@patch("starlite.cache.redis_cache_backend.ConnectionPool.from_url")
@patch("starlite.cache.redis_cache_backend.Redis")
def test_config_redis_non_default(_redis_mock: Mock, connection_pool_from_url_mock: Mock) -> None:
    url = "redis://localhost"
    db = 2
    port = 1234
    username = "user"
    password = "password"
    config = RedisCacheBackendConfig(
        url=url, db=db,  port=port, username=username, password=password
    )
    cache = RedisCacheBackend(config)
    assert cache._redis
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=db, port=port, username=username, password=password
    )


@patch("starlite.cache.redis_cache_backend.RedisCacheBackend._redis")
async def test_get_from_cache(redis_mock: Mock):
    key = "key"
    value = "value"
    fake_redis = FakeAsyncRedis()
    await fake_redis.set(key, value, 60)

    redis_mock.get = fake_redis.get

    config = RedisCacheBackendConfig(url="url")
    cache = RedisCacheBackend(config)

    cached_value = await cache.get(key)
    assert cached_value == value


@patch("starlite.cache.redis_cache_backend.RedisCacheBackend._redis")
async def test_set_in_cache(redis_mock: Mock):
    key = "key"
    value = "value"
    exp = 60

    fake_redis = FakeAsyncRedis()

    redis_mock.set = fake_redis.set

    config = RedisCacheBackendConfig(url="url")
    cache = RedisCacheBackend(config)

    await cache.set(key, value, exp)
    fake_redis_value = await fake_redis.get(key)
    assert fake_redis_value == value
    assert fake_redis.ttl(key) == exp


@patch("starlite.cache.redis_cache_backend.RedisCacheBackend._redis")
async def test_delete_from_cache(redis_mock: Mock):
    key = "key"
    fake_redis = FakeAsyncRedis()
    await fake_redis.set(key, "value", 60)

    redis_mock.delete = fake_redis.delete

    config = RedisCacheBackendConfig(url="url")
    cache = RedisCacheBackend(config)

    await cache.delete(key)
    fake_redis_value = await fake_redis.get(key)
    assert fake_redis_value is None
