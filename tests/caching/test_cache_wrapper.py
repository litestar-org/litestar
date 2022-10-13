from asyncio import sleep
from datetime import datetime, timedelta
from typing import Any, Dict

import pytest

from starlite.cache import Cache, CacheBackendProtocol, SimpleCacheBackend
from starlite.cache.simple_cache_backend import CacheObject
from starlite.config.cache import default_cache_key_builder


class NaiveCacheBackend(CacheBackendProtocol):
    def __init__(self) -> None:
        self._store: Dict[str, CacheObject] = {}

    def get(self, key: str) -> Any:
        cache_obj = self._store.get(key)
        if cache_obj:
            if cache_obj.expiration >= datetime.now():
                return cache_obj.value
            self.delete(key)
        return None

    def set(self, key: str, value: Any, expiration: int) -> None:
        self._store[key] = CacheObject(value=value, expiration=datetime.now() + timedelta(seconds=expiration))

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.mark.parametrize("backend", [SimpleCacheBackend(), NaiveCacheBackend()])
async def test_cache_wrapper_integration(backend: CacheBackendProtocol, anyio_backend: str) -> None:
    value_to_cache = "123"
    cache = Cache(backend=backend, default_expiration=1, cache_key_builder=default_cache_key_builder)
    await cache.set("test-key", value_to_cache)
    assert (await cache.get("test-key")) == value_to_cache
    await cache.delete("test-key")
    assert (await cache.get("test-key")) is None


@pytest.mark.parametrize("backend", [SimpleCacheBackend(), NaiveCacheBackend()])
async def test_cache_wrapper_default_expiration(backend: CacheBackendProtocol, anyio_backend: str) -> None:
    value_to_cache = "123"
    cache = Cache(backend=backend, default_expiration=0.1, cache_key_builder=default_cache_key_builder)  # type: ignore
    await cache.set("test-key", value_to_cache)
    assert (await cache.get("test-key")) == value_to_cache
    await sleep(0.2)
    assert (await cache.get("test-key")) is None


@pytest.mark.parametrize("backend", [SimpleCacheBackend(), NaiveCacheBackend()])
async def test_cache_wrapper_custom_expiration(backend: CacheBackendProtocol, anyio_backend: str) -> None:
    value_to_cache = "123"
    cache = Cache(backend=backend, default_expiration=1, cache_key_builder=default_cache_key_builder)
    await cache.set("test-key", value=value_to_cache, expiration=0.1)  # type: ignore
    assert (await cache.get("test-key")) == value_to_cache
    await sleep(0.2)
    assert (await cache.get("test-key")) is None
