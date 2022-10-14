import pickle
from typing import TYPE_CHECKING, Optional
from unittest.mock import Mock, patch

from starlite.cache.memcached_cache_backend import (
    MemcachedCacheBackend,
    MemcachedCacheBackendConfig,
)

if TYPE_CHECKING:
    from typing import Dict


class FakeAsyncMemcached:
    def __init__(self) -> None:
        self._cache: Dict[bytes, bytes] = {}
        self._expirations: Dict[bytes, int] = {}

    async def get(self, key: bytes) -> Optional[bytes]:
        return self._cache.get(key)

    async def set(self, key: bytes, value: bytes, expiration: int) -> None:
        self._cache[key] = value
        self._expirations[key] = expiration

    async def delete(self, key: bytes) -> None:
        self._cache.pop(key)

    def ttl(self, key: bytes) -> Optional[int]:
        return self._expirations.get(key)


@patch("starlite.cache.memcached_cache_backend.Client")
def test_config_memcached_default(memcached_client_mock: Mock) -> None:
    host = "127.0.0.1"
    config = MemcachedCacheBackendConfig(host=host)
    cache = MemcachedCacheBackend(config)
    assert cache._memcached_client
    memcached_client_mock.assert_called_once_with(host=host)


@patch("starlite.cache.memcached_cache_backend.Client")
def test_config_memcached_non_default(memcached_client_mock: Mock) -> None:
    host = "127.0.0.1"
    port = 22122
    pool_size = 10
    pool_minsize = 7
    config = MemcachedCacheBackendConfig(host=host, port=port, pool_size=pool_size, pool_minsize=pool_minsize)
    cache = MemcachedCacheBackend(config)
    assert cache._memcached_client
    memcached_client_mock.assert_called_once_with(host=host, port=port, pool_size=pool_size, pool_minsize=pool_minsize)


@patch("starlite.cache.memcached_cache_backend.MemcachedCacheBackend._memcached_client")
async def test_get_from_cache(memcached_client_mock: Mock) -> None:
    key = "key"
    value = "value"
    fake_memcached = FakeAsyncMemcached()
    await fake_memcached.set(key.encode(), pickle.dumps(value), 60)

    memcached_client_mock.get = fake_memcached.get

    config = MemcachedCacheBackendConfig(host="host")
    cache = MemcachedCacheBackend(config)

    cached_value = await cache.get(key)
    assert cached_value == value


@patch("starlite.cache.memcached_cache_backend.MemcachedCacheBackend._memcached_client")
async def test_set_in_cache(memcached_client_mock: Mock) -> None:
    key = "key"
    value = "value"
    exp = 60

    fake_memcached = FakeAsyncMemcached()

    memcached_client_mock.set = fake_memcached.set

    config = MemcachedCacheBackendConfig(host="host")
    cache = MemcachedCacheBackend(config)

    await cache.set(key, value, exp)
    fake_memcached_value = await fake_memcached.get(key.encode())
    assert fake_memcached_value == pickle.dumps(value)
    assert fake_memcached.ttl(key.encode()) == exp


@patch("starlite.cache.memcached_cache_backend.MemcachedCacheBackend._memcached_client")
async def test_delete_from_cache(memcached_client_mock: Mock) -> None:
    key = "key"
    fake_memcached = FakeAsyncMemcached()
    await fake_memcached.set(key.encode(), b"value", 60)

    memcached_client_mock.delete = fake_memcached.delete

    config = MemcachedCacheBackendConfig(host="host")
    cache = MemcachedCacheBackend(config)

    await cache.delete(key)
    fake_memcached_value = await fake_memcached.get(key.encode())
    assert fake_memcached_value is None


@patch("starlite.cache.memcached_cache_backend.MemcachedCacheBackend._memcached_client")
async def test_non_default_serialization(memcached_client_mock: Mock) -> None:
    serialized_data = b"serialized"
    deserialized_data = "deserialized"

    key = "key"
    fake_memcached = FakeAsyncMemcached()

    memcached_client_mock.set = fake_memcached.set
    memcached_client_mock.get = fake_memcached.get

    config = MemcachedCacheBackendConfig(
        host="host", serialize=lambda _: serialized_data, deserialize=lambda _: deserialized_data
    )
    cache = MemcachedCacheBackend(config)

    await cache.set(key, "value", 60)
    serialized_cached_data = await fake_memcached.get(key.encode())
    assert serialized_cached_data == serialized_data

    deserialized_cached_data = await cache.get(key)
    assert deserialized_cached_data == deserialized_data
