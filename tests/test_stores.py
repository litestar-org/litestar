from __future__ import annotations

import math
import shutil
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import anyio
import pytest
from _pytest.fixtures import FixtureRequest

from starlite.exceptions import ImproperlyConfiguredException
from starlite.stores.file import FileStore
from starlite.stores.redis import RedisStore

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from starlite.stores.base import Store


@pytest.fixture()
def mock_redis() -> None:
    patch("starlite.Store.redis_backend.Redis")


async def test_get(store: Store) -> None:
    key = "key"
    value = b"value"
    assert await store.get("foo") is None

    await store.set(key, value, 60)

    stored_value = await store.get(key)
    assert stored_value == value


async def test_set(store: Store) -> None:
    values: dict[str, bytes | str] = {"key_1": b"value_1", "key_2": "value_2"}

    for key, value in values.items():
        await store.set(key, value)

    for key, value in values.items():
        stored_value = await store.get(key)
        assert stored_value == value if isinstance(value, bytes) else value.encode("utf-8")


async def test_expires(store: Store) -> None:
    expiry = 0.01 if not isinstance(store, RedisStore) else 1  # redis doesn't allow fractional values
    await store.set("foo", b"bar", expires_in=expiry)  # type: ignore[arg-type]

    await anyio.sleep(expiry + 0.01)

    stored_value = await store.get("foo")

    assert stored_value is None


@pytest.mark.parametrize("renew_for", [10, timedelta(seconds=10)])
async def test_get_and_renew(store: Store, renew_for: int | timedelta) -> None:
    await store.set("foo", b"bar", expires_in=1)
    await store.get("foo", renew_for=renew_for)
    await anyio.sleep(1.01)

    stored_value = await store.get("foo")

    assert stored_value is not None


async def test_delete(store: Store) -> None:
    key = "key"
    await store.set(key, b"value", 60)

    await store.delete(key)

    fake_redis_value = await store.get(key)
    assert fake_redis_value is None


async def test_delete_empty(store: Store) -> None:
    # assert that this does not raise an exception
    await store.delete("foo")


async def test_exists(store: Store) -> None:
    assert await store.exists("foo") is False

    await store.set("foo", b"bar")

    assert await store.exists("foo") is True


async def test_expires_in_not_set(store: Store) -> None:
    assert await store.expires_in("foo") is None

    await store.set("foo", b"bar")
    assert await store.expires_in("foo") == -1


async def test_delete_all(store: Store) -> None:
    keys = []
    for i in range(10):
        key = f"key-{i}"
        keys.append(key)
        await store.set(key, b"value", expires_in=10 if i % 2 else None)

    await store.delete_all()

    assert not any([await store.get(key) for key in keys])


async def test_expires_in(store: Store) -> None:
    assert await store.expires_in("foo") is None

    await store.set("foo", "bar")
    assert await store.expires_in("foo") == -1

    await store.set("foo", "bar", expires_in=10)
    assert math.ceil(await store.expires_in("foo") / 10) * 10 == 10  # type: ignore[operator]


@patch("starlite.stores.redis.Redis")
@patch("starlite.stores.redis.ConnectionPool.from_url")
def test_redis_backend_with_client_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
    url = "redis://localhost"
    backend = RedisStore.with_client(url=url)
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=None, port=None, username=None, password=None, decode_responses=False
    )
    mock_redis.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._redis is mock_redis.return_value


@patch("starlite.stores.redis.Redis")
@patch("starlite.stores.redis.ConnectionPool.from_url")
def test_redis_backend_with_non_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
    url = "redis://localhost"
    db = 2
    port = 1234
    username = "user"
    password = "password"
    backend = RedisStore.with_client(url=url, db=db, port=port, username=username, password=password)
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=db, port=port, username=username, password=password, decode_responses=False
    )
    mock_redis.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._redis is mock_redis.return_value


async def test_file_backend_init_directory(file_store: FileStore) -> None:
    shutil.rmtree(file_store.path)
    await file_store.set("foo", b"bar")


async def test_file_backend_path(file_store: FileStore) -> None:
    await file_store.set("foo", b"bar")

    assert await (file_store.path / "foo").exists()


async def test_redis_namespaced_get_set(redis_store: RedisStore) -> None:
    foo_namespaced = redis_store.with_namespace("foo")
    await redis_store.set("foo", b"starlite namespace")
    await foo_namespaced.set("foo", b"foo namespace")

    assert await redis_store.get("foo") == b"starlite namespace"
    assert await foo_namespaced.get("foo") == b"foo namespace"


async def test_redis_delete_all(redis_store: RedisStore) -> None:
    await redis_store._redis.set("test_key", b"test_value")

    keys = []
    for i in range(10):
        key = f"key-{i}"
        keys.append(key)
        await redis_store.set(key, b"value", expires_in=10 if i % 2 else None)

    await redis_store.delete_all()

    assert not any([await redis_store.get(key) for key in keys])
    assert await redis_store._redis.get("test_key") == b"test_value"  # check it doesn't delete other values


async def test_redis_delete_all_namespace_does_not_propagate_up(redis_store: RedisStore) -> None:
    foo_namespace = redis_store.with_namespace("FOO")
    await foo_namespace.set("foo", b"foo-value")
    await redis_store.set("bar", b"bar-value")

    await foo_namespace.delete_all()

    assert await foo_namespace.get("foo") is None
    assert await redis_store.get("bar") == b"bar-value"


async def test_redis_delete_all_namespace_propagates_down(redis_store: RedisStore) -> None:
    foo_namespace = redis_store.with_namespace("FOO")
    await foo_namespace.set("foo", b"foo-value")
    await redis_store.set("bar", b"bar-value")

    await redis_store.delete_all()

    assert await foo_namespace.get("foo") is None
    assert await redis_store.get("bar") is None


async def test_redis_delete_all_no_namespace_raises(fake_redis: Redis) -> None:
    redis_store = RedisStore(redis=fake_redis, namespace=None)

    with pytest.raises(ImproperlyConfiguredException):
        await redis_store.delete_all()


def test_redis_namespaced_key(redis_store: RedisStore) -> None:
    assert redis_store.namespace == "STARLITE"
    assert redis_store._make_key("foo") == "STARLITE:foo"


def test_redis_with_namespace(redis_store: RedisStore) -> None:
    namespaced_test = redis_store.with_namespace("TEST")
    namespaced_test_foo = namespaced_test.with_namespace("FOO")
    assert namespaced_test.namespace == "STARLITE_TEST"
    assert namespaced_test_foo.namespace == "STARLITE_TEST_FOO"
    assert namespaced_test._redis is redis_store._redis


def test_redis_namespace_explicit_none(fake_redis: Redis) -> None:
    assert RedisStore.with_client(url="redis://127.0.0.1", namespace=None).namespace is None
    assert RedisStore(redis=fake_redis, namespace=None).namespace is None


@pytest.mark.parametrize("store_fixture", ["memory_store", "file_store"])
async def test_memory_delete_expired(store_fixture: str, request: FixtureRequest) -> None:
    store = request.getfixturevalue(store_fixture)

    expect_expired: list[str] = []
    expect_not_expired: list[str] = []
    for i in range(10):
        key = f"key-{i}"
        expires_in = 0.001 if i % 2 == 0 else None
        await store.set(key, b"value", expires_in=expires_in)
        (expect_expired if expires_in else expect_not_expired).append(key)

    await anyio.sleep(0.002)
    await store.delete_expired()

    assert not any([await store.exists(key) for key in expect_expired])
    assert all([await store.exists(key) for key in expect_not_expired])
