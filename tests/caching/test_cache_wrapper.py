from asyncio import sleep

import pytest

from starlite.cache import Cache
from starlite.config.cache import default_cache_key_builder
from starlite.storage.memory import MemoryStorage


@pytest.fixture()
def backend() -> MemoryStorage:
    return MemoryStorage()


async def test_cache_wrapper_integration(backend: MemoryStorage) -> None:
    value_to_cache = b"123"
    cache = Cache(backend=backend, default_expiration=1, cache_key_builder=default_cache_key_builder)
    await cache.set("test-key", value_to_cache)
    assert (await cache.get("test-key")) == value_to_cache
    await cache.delete("test-key")
    assert (await cache.get("test-key")) is None


async def test_cache_wrapper_default_expiration(backend: MemoryStorage) -> None:
    value_to_cache = b"123"
    cache = Cache(backend=backend, default_expiration=0.1, cache_key_builder=default_cache_key_builder)  # type: ignore
    await cache.set("test-key", value_to_cache)
    assert (await cache.get("test-key")) == value_to_cache
    await sleep(0.2)
    assert (await cache.get("test-key")) is None


async def test_cache_wrapper_custom_expiration(backend: MemoryStorage) -> None:
    value_to_cache = b"123"
    cache = Cache(backend=backend, default_expiration=1, cache_key_builder=default_cache_key_builder)
    await cache.set("test-key", value=value_to_cache, expiration=0.1)  # type: ignore
    assert (await cache.get("test-key")) == value_to_cache
    await sleep(0.2)
    assert (await cache.get("test-key")) is None
