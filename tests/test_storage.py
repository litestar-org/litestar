from __future__ import annotations

import shutil
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import anyio
import pytest
from _pytest.fixtures import FixtureRequest

from starlite.exceptions import ImproperlyConfiguredException
from starlite.storage.redis import RedisStorage

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from starlite.storage.base import Storage
    from starlite.storage.file import FileStorage


@pytest.fixture()
def mock_redis() -> None:
    patch("starlite.storage.redis_backend.Redis")


async def test_get(storage_backend: Storage) -> None:
    key = "key"
    value = b"value"
    await storage_backend.set(key, value, 60)

    stored_value = await storage_backend.get(key)
    assert stored_value == value


async def test_set(storage_backend: Storage) -> None:
    values = {"key_1": b"value_1", "key_2": b"value_2"}

    for key, value in values.items():
        await storage_backend.set(key, value)

    for key, value in values.items():
        stored_value = await storage_backend.get(key)
        assert stored_value == value


async def test_expires(storage_backend: Storage) -> None:
    expiry = 0.01 if not isinstance(storage_backend, RedisStorage) else 1  # redis doesn't allow fractional values
    await storage_backend.set("foo", b"bar", expires_in=expiry)  # type: ignore[arg-type]

    await anyio.sleep(expiry + 0.01)

    stored_value = await storage_backend.get("foo")

    assert stored_value is None


async def test_get_and_renew(storage_backend: Storage) -> None:
    expiry = 0.01 if not isinstance(storage_backend, RedisStorage) else 1  # redis doesn't allow fractional values
    await storage_backend.set("foo", b"bar", expires_in=expiry)  # type: ignore[arg-type]
    await storage_backend.get("foo", renew_for=10)
    await anyio.sleep(expiry + 0.01)

    stored_value = await storage_backend.get("foo")

    assert stored_value is not None


async def test_delete(storage_backend: Storage) -> None:
    key = "key"
    await storage_backend.set(key, b"value", 60)

    await storage_backend.delete(key)

    fake_redis_value = await storage_backend.get(key)
    assert fake_redis_value is None


async def test_delete_empty(storage_backend: Storage) -> None:
    # assert that this does not raise an exception
    await storage_backend.delete("foo")


async def test_exists(storage_backend: Storage) -> None:
    assert await storage_backend.exists("foo") is False

    await storage_backend.set("foo", b"bar")

    assert await storage_backend.exists("foo") is True


async def test_expires_in_not_set(storage_backend: Storage) -> None:
    assert await storage_backend.expires_in("foo") is None

    await storage_backend.set("foo", b"bar")
    assert await storage_backend.expires_in("foo") == -1


@patch("starlite.storage.redis.Redis")
@patch("starlite.storage.redis.ConnectionPool.from_url")
def test_redis_backend_with_client_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
    url = "redis://localhost"
    backend = RedisStorage.with_client(url=url)
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=None, port=None, username=None, password=None, decode_responses=False
    )
    mock_redis.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._redis is mock_redis.return_value


@patch("starlite.storage.redis.Redis")
@patch("starlite.storage.redis.ConnectionPool.from_url")
def test_redis_backend_with_non_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
    url = "redis://localhost"
    db = 2
    port = 1234
    username = "user"
    password = "password"
    backend = RedisStorage.with_client(url=url, db=db, port=port, username=username, password=password)
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=db, port=port, username=username, password=password, decode_responses=False
    )
    mock_redis.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._redis is mock_redis.return_value


async def test_file_backend_init_directory(file_storage_backend: FileStorage) -> None:
    shutil.rmtree(file_storage_backend.path)
    await file_storage_backend.set("foo", b"bar")


async def test_file_backend_path(file_storage_backend: FileStorage) -> None:
    await file_storage_backend.set("foo", b"bar")

    assert await (file_storage_backend.path / "foo").exists()


async def test_redis_namespaced_get_set(redis_storage_backend: RedisStorage) -> None:
    foo_namespaced = redis_storage_backend.with_namespace("foo")
    await redis_storage_backend.set("foo", b"starlite namespace")
    await foo_namespaced.set("foo", b"foo namespace")

    assert await redis_storage_backend.get("foo") == b"starlite namespace"
    assert await foo_namespaced.get("foo") == b"foo namespace"


async def test_redis_delete_all(redis_storage_backend: RedisStorage) -> None:
    await redis_storage_backend._redis.set("test_key", b"test_value")

    keys = []
    for i in range(10):
        key = f"key-{i}"
        keys.append(key)
        await redis_storage_backend.set(key, b"value", expires_in=10 if i % 2 else None)

    await redis_storage_backend.delete_all()

    assert not any([await redis_storage_backend.get(key) for key in keys])
    assert await redis_storage_backend._redis.get("test_key") == b"test_value"  # check it doesn't delete other values


async def test_redis_delete_all_namespace_does_not_propagate_up(redis_storage_backend: RedisStorage) -> None:
    foo_namespace = redis_storage_backend.with_namespace("FOO")
    await foo_namespace.set("foo", b"foo-value")
    await redis_storage_backend.set("bar", b"bar-value")

    await foo_namespace.delete_all()

    assert await foo_namespace.get("foo") is None
    assert await redis_storage_backend.get("bar") == b"bar-value"


async def test_redis_delete_all_namespace_propagates_down(redis_storage_backend: RedisStorage) -> None:
    foo_namespace = redis_storage_backend.with_namespace("FOO")
    await foo_namespace.set("foo", b"foo-value")
    await redis_storage_backend.set("bar", b"bar-value")

    await redis_storage_backend.delete_all()

    assert await foo_namespace.get("foo") is None
    assert await redis_storage_backend.get("bar") is None


async def test_redis_delete_all_no_namespace_raises(fake_redis: Redis) -> None:
    redis_storage_backend = RedisStorage(redis=fake_redis, namespace=None)

    with pytest.raises(ImproperlyConfiguredException):
        await redis_storage_backend.delete_all()


def test_redis_namespaced_key(redis_storage_backend: RedisStorage) -> None:
    assert redis_storage_backend.namespace == "STARLITE"
    assert redis_storage_backend._make_key("foo") == "STARLITE:foo"


def test_redis_with_namespace(redis_storage_backend: RedisStorage) -> None:
    namespaced_test = redis_storage_backend.with_namespace("TEST")
    namespaced_test_foo = namespaced_test.with_namespace("FOO")
    assert namespaced_test.namespace == "STARLITE_TEST"
    assert namespaced_test_foo.namespace == "STARLITE_TEST_FOO"
    assert namespaced_test._redis is redis_storage_backend._redis


def test_redis_namespace_explicit_none(fake_redis: Redis) -> None:
    assert RedisStorage.with_client(url="redis://127.0.0.1", namespace=None).namespace is None
    assert RedisStorage(redis=fake_redis, namespace=None).namespace is None


@pytest.mark.parametrize("storage_backend_fixture", ["memory_storage_backend", "file_storage_backend"])
async def test_memory_delete_expired(storage_backend_fixture: str, request: FixtureRequest) -> None:
    storage_backend = request.getfixturevalue(storage_backend_fixture)

    expect_expired: list[str] = []
    expect_not_expired: list[str] = []
    for i in range(10):
        key = f"key-{i}"
        expires_in = 0.001 if i % 2 == 0 else None
        await storage_backend.set(key, b"value", expires_in=expires_in)
        (expect_expired if expires_in else expect_not_expired).append(key)

    await anyio.sleep(0.002)
    await storage_backend.delete_expired()

    assert not any([await storage_backend.exists(key) for key in expect_expired])
    assert all([await storage_backend.exists(key) for key in expect_not_expired])
