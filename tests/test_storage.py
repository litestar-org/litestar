from __future__ import annotations

import shutil
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import anyio
import pytest

from starlite.storage.memcached_backend import MemcachedStorageBackend
from starlite.storage.redis_backend import RedisStorageBackend

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from starlite.storage.base import StorageBackend
    from starlite.storage.file_backend import FileStorageBackend
    from tests.mocks import FakeAsyncMemcached


@pytest.fixture()
def mock_redis() -> None:
    patch("starlite.storage.redis_backend.Redis")


async def test_get_from_cache(storage_backend: StorageBackend) -> None:
    key = "key"
    value = b"value"
    await storage_backend.set(key, value, 60)

    stored_value = await storage_backend.get(key)
    assert stored_value == value


async def test_set_in_cache(storage_backend: StorageBackend) -> None:
    values = {"key_1": b"value_1", "key_2": b"value_2"}

    for key, value in values.items():
        await storage_backend.set(key, value)

    for key, value in values.items():
        stored_value = await storage_backend.get(key)
        assert stored_value == value


async def test_expires(storage_backend: StorageBackend) -> None:
    expiry = (
        0.01 if not isinstance(storage_backend, RedisStorageBackend) else 1
    )  # redis doesn't allow fractional values
    await storage_backend.set("foo", b"bar", expires=expiry)

    await anyio.sleep(expiry + 0.01)

    stored_value = await storage_backend.get("foo")

    assert stored_value is None


async def test_delete_from_cache(storage_backend: StorageBackend) -> None:
    key = "key"
    await storage_backend.set(key, b"value", 60)

    await storage_backend.delete(key)

    fake_redis_value = await storage_backend.get(key)
    assert fake_redis_value is None


async def test_delete_empty(storage_backend: StorageBackend) -> None:
    # assert that this does not raise an exception
    await storage_backend.delete("foo")


@patch("starlite.storage.memcached_backend.Client")
def test_memcached_backend_with_client_default(memcached_mock: Mock) -> None:
    host = "127.0.0.1"
    backend = MemcachedStorageBackend.with_client(host=host)
    assert backend._memcached
    memcached_mock.assert_called_once_with(host=host, pool_minsize=None, pool_size=2, port=11211)


@patch("starlite.storage.memcached_backend.Client")
def test_memcached_backend_with_client_non_default(memcached_mock: Mock) -> None:
    host = "127.0.0.1"
    port = 22122
    pool_size = 10
    pool_minsize = 7
    backend = MemcachedStorageBackend.with_client(host=host, port=port, pool_size=pool_size, pool_minsize=pool_minsize)
    assert backend._memcached
    memcached_mock.assert_called_once_with(host=host, port=port, pool_size=pool_size, pool_minsize=pool_minsize)


@patch("starlite.storage.redis_backend.ConnectionPool.from_url")
@pytest.mark.usefixtures("mock_redis")
def test_redis_backend_with_client_default(connection_pool_from_url_mock: Mock) -> None:
    url = "redis://localhost"
    cache = RedisStorageBackend.with_client(url=url)
    assert cache._redis
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=None, port=None, username=None, password=None, decode_responses=False
    )


@patch("starlite.storage.redis_backend.ConnectionPool.from_url")
@pytest.mark.usefixtures("mock_redis")
def test_redis_backend_with_non_default(connection_pool_from_url_mock: Mock) -> None:
    url = "redis://localhost"
    db = 2
    port = 1234
    username = "user"
    password = "password"
    cache = RedisStorageBackend.with_client(url=url, db=db, port=port, username=username, password=password)
    assert cache._redis
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=db, port=port, username=username, password=password, decode_responses=False
    )


async def test_file_backend_init_directory(file_storage_backend: FileStorageBackend) -> None:
    shutil.rmtree(file_storage_backend.path)
    await file_storage_backend.set("foo", b"bar")


async def test_file_backend_path(file_storage_backend: FileStorageBackend) -> None:
    await file_storage_backend.set("foo", b"bar")

    assert await (file_storage_backend.path / "foo").exists()


def test_redis_namespaced_key(redis_storage_backend: RedisStorageBackend) -> None:
    assert redis_storage_backend.namespace == "STARLITE"
    assert redis_storage_backend.make_key("foo") == "STARLITE_foo"


def test_redis_with_namespace(redis_storage_backend: RedisStorageBackend) -> None:
    namespaced = redis_storage_backend.with_namespace("TEST")
    assert namespaced.namespace == "STARLITE_TEST"
    assert namespaced._redis is redis_storage_backend._redis


def test_redis_namespace_explicit_none(fake_redis: Redis) -> None:
    assert RedisStorageBackend.with_client(url="redis://127.0.0.1", namespace=None).namespace is None
    assert RedisStorageBackend(redis=fake_redis, namespace=None).namespace is None


def test_memcached_namespaced_key(memcached_storage_backend: MemcachedStorageBackend) -> None:
    assert memcached_storage_backend.namespace == "STARLITE"
    assert memcached_storage_backend.make_key("foo") == "STARLITE_foo"


def test_memcached_with_namespace(memcached_storage_backend: MemcachedStorageBackend) -> None:
    namespaced = memcached_storage_backend.with_namespace("TEST")
    assert namespaced.namespace == "STARLITE_TEST"
    assert namespaced._memcached is memcached_storage_backend._memcached


def test_memcached_namespace_explicit_none(fake_async_memcached: FakeAsyncMemcached) -> None:
    assert MemcachedStorageBackend.with_client(host="127.0.0.1", namespace=None).namespace is None
    assert MemcachedStorageBackend(memcached=fake_async_memcached, namespace=None).namespace is None
