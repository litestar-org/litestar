from __future__ import annotations

import shutil
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import anyio
import pytest

from starlite.storage.redis_backend import RedisStorageBackend

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from starlite.storage.base import StorageBackend
    from starlite.storage.file_backend import FileStorageBackend


@pytest.fixture()
def mock_redis() -> None:
    patch("starlite.storage.redis_backend.Redis")


async def test_get(storage_backend: StorageBackend) -> None:
    key = "key"
    value = b"value"
    await storage_backend.set(key, value, 60)

    stored_value = await storage_backend.get(key)
    assert stored_value == value


async def test_set(storage_backend: StorageBackend) -> None:
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
    await storage_backend.set("foo", b"bar", expires_in=expiry)  # type: ignore[arg-type]

    await anyio.sleep(expiry + 0.01)

    stored_value = await storage_backend.get("foo")

    assert stored_value is None


async def test_get_and_renew(storage_backend: StorageBackend) -> None:
    expiry = (
        0.01 if not isinstance(storage_backend, RedisStorageBackend) else 1
    )  # redis doesn't allow fractional values
    await storage_backend.set("foo", b"bar", expires_in=expiry)  # type: ignore[arg-type]
    await storage_backend.get("foo", renew_for=10)
    await anyio.sleep(expiry + 0.01)

    stored_value = await storage_backend.get("foo")

    assert stored_value is not None


async def test_delete(storage_backend: StorageBackend) -> None:
    key = "key"
    await storage_backend.set(key, b"value", 60)

    await storage_backend.delete(key)

    fake_redis_value = await storage_backend.get(key)
    assert fake_redis_value is None


async def test_delete_empty(storage_backend: StorageBackend) -> None:
    # assert that this does not raise an exception
    await storage_backend.delete("foo")


@patch("starlite.storage.redis_backend.Redis")
@patch("starlite.storage.redis_backend.ConnectionPool.from_url")
def test_redis_backend_with_client_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
    url = "redis://localhost"
    backend = RedisStorageBackend.with_client(url=url)
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=None, port=None, username=None, password=None, decode_responses=False
    )
    mock_redis.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._redis is mock_redis.return_value


@patch("starlite.storage.redis_backend.Redis")
@patch("starlite.storage.redis_backend.ConnectionPool.from_url")
def test_redis_backend_with_non_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
    url = "redis://localhost"
    db = 2
    port = 1234
    username = "user"
    password = "password"
    backend = RedisStorageBackend.with_client(url=url, db=db, port=port, username=username, password=password)
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=db, port=port, username=username, password=password, decode_responses=False
    )
    mock_redis.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._redis is mock_redis.return_value


async def test_file_backend_init_directory(file_storage_backend: FileStorageBackend) -> None:
    shutil.rmtree(file_storage_backend.path)
    await file_storage_backend.set("foo", b"bar")


async def test_file_backend_path(file_storage_backend: FileStorageBackend) -> None:
    await file_storage_backend.set("foo", b"bar")

    assert await (file_storage_backend.path / "foo").exists()


async def test_redis_delete_all(redis_storage_backend: RedisStorageBackend) -> None:
    keys = []
    for i in range(10):
        key = f"key-{i}"
        keys.append(key)
        await redis_storage_backend.set(key, b"value", expires_in=10 if i % 2 else None)

    await redis_storage_backend.delete_all()

    assert not any([await redis_storage_backend.get(key) for key in keys])


def test_redis_namespaced_key(redis_storage_backend: RedisStorageBackend) -> None:
    assert redis_storage_backend.namespace == "STARLITE"
    assert redis_storage_backend.make_key("foo") == "STARLITE:foo"


def test_redis_with_namespace(redis_storage_backend: RedisStorageBackend) -> None:
    namespaced = redis_storage_backend.with_namespace("TEST")
    assert namespaced.namespace == "STARLITE_TEST"
    assert namespaced._redis is redis_storage_backend._redis


def test_redis_namespace_explicit_none(fake_redis: Redis) -> None:
    assert RedisStorageBackend.with_client(url="redis://127.0.0.1", namespace=None).namespace is None
    assert RedisStorageBackend(redis=fake_redis, namespace=None).namespace is None
