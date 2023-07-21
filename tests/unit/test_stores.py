from __future__ import annotations

import math
import shutil
import string
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, Mock, patch

import pytest
from _pytest.fixtures import FixtureRequest
from freezegun.api import FakeDatetime, FrozenDateTimeFactory  # type: ignore[attr-defined]
from msgspec.msgpack import decode as decode_msgpack
from pytest_mock import MockerFixture
from redis.asyncio import Redis as AsyncRedis

from litestar.exceptions import ImproperlyConfiguredException
from litestar.serialization import encode_msgpack
from litestar.stores.file import FileStore
from litestar.stores.memory import MemoryStore
from litestar.stores.redis import RedisStore
from litestar.stores.registry import StoreRegistry

if TYPE_CHECKING:
    from litestar.stores.base import NamespacedStore, Store


@pytest.fixture()
def mock_redis() -> None:
    patch("litestar.Store.redis_backend.Redis")


@pytest.fixture()
def patch_storage_obj_frozen_datetime(mocker: MockerFixture) -> None:
    def _msgpack_encode(data: Any) -> bytes:
        def enc_hook(value: Any) -> Any:
            if isinstance(value, FakeDatetime):
                return value.isoformat()
            raise TypeError()

        return encode_msgpack(data, serializer=enc_hook)

    def _msgpack_decode(data: Any, type: Any) -> Any:
        def dec_hook(value_type: Any, value: Any) -> Any:
            if value_type is FakeDatetime:
                return FakeDatetime.fromisoformat(value)
            raise TypeError()

        return decode_msgpack(data, type=type, dec_hook=dec_hook)

    mocker.patch("litestar.stores.base.msgpack_encode", _msgpack_encode)
    mocker.patch("litestar.stores.base.msgpack_decode", _msgpack_decode)


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


@pytest.mark.parametrize("key", [*list(string.punctuation), "foo\xc3\xbc", ".."])
async def test_set_special_chars_key(store: Store, key: str) -> None:
    # ensure that stores handle special chars correctly
    value = b"value"

    await store.set(key, value)
    assert await store.get(key) == value


@pytest.mark.usefixtures("patch_storage_obj_frozen_datetime")
async def test_expires(store: Store, frozen_datetime: FrozenDateTimeFactory) -> None:
    await store.set("foo", b"bar", expires_in=1)

    frozen_datetime.tick(2)

    if isinstance(store, RedisStore):
        # mocking the time doesn't affect the expiry timeout on the Redis instance
        await store._redis.expire(f"{store.namespace}:foo", 0)

    stored_value = await store.get("foo")

    assert stored_value is None


@pytest.mark.usefixtures("patch_storage_obj_frozen_datetime")
@pytest.mark.parametrize("renew_for", [10, timedelta(seconds=10)])
async def test_get_and_renew(store: Store, renew_for: int | timedelta, frozen_datetime: FrozenDateTimeFactory) -> None:
    await store.set("foo", b"bar", expires_in=1)
    await store.get("foo", renew_for=renew_for)

    frozen_datetime.tick(2)

    stored_value = await store.get("foo")

    assert stored_value is not None


async def test_delete(store: Store) -> None:
    key = "key"
    await store.set(key, b"value", 60)

    await store.delete(key)

    value = await store.get(key)
    assert value is None


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

    for key in keys:
        assert await store.get(key) is None


@pytest.mark.usefixtures("patch_storage_obj_frozen_datetime")
async def test_expires_in(store: Store, frozen_datetime: FrozenDateTimeFactory) -> None:
    if not isinstance(store, RedisStore):
        pytest.xfail("bug in FileStore and MemoryStore")

    assert await store.expires_in("foo") is None

    await store.set("foo", "bar")
    assert await store.expires_in("foo") == -1

    await store.set("foo", "bar", expires_in=10)
    expiration = await store.expires_in("foo")
    assert expiration is not None
    assert math.ceil(expiration / 10) == 1

    await store._redis.expire(f"{store.namespace}:foo", 0)
    expiration = await store.expires_in("foo")
    assert expiration is None


@patch("litestar.stores.redis.Redis")
@patch("litestar.stores.redis.ConnectionPool.from_url")
def test_redis_with_client_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
    backend = RedisStore.with_client()
    connection_pool_from_url_mock.assert_called_once_with(
        url="redis://localhost:6379", db=None, port=None, username=None, password=None, decode_responses=False
    )
    mock_redis.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._redis is mock_redis.return_value


@patch("litestar.stores.redis.Redis")
@patch("litestar.stores.redis.ConnectionPool.from_url")
def test_redis_with_non_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
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


async def test_redis_delete_all(redis_store: RedisStore) -> None:
    await redis_store._redis.set("test_key", b"test_value")

    keys = []
    for i in range(10):
        key = f"key-{i}"
        keys.append(key)
        await redis_store.set(key, b"value", expires_in=10 if i % 2 else None)

    await redis_store.delete_all()

    for key in keys:
        assert await redis_store.get(key) is None

    stored_value = await redis_store._redis.get("test_key")
    assert stored_value == b"test_value"  # check it doesn't delete other values


async def test_redis_delete_all_no_namespace_raises(redis_client: AsyncRedis) -> None:
    redis_store = RedisStore(redis=redis_client, namespace=None)

    with pytest.raises(ImproperlyConfiguredException):
        await redis_store.delete_all()


def test_redis_namespaced_key(redis_store: RedisStore) -> None:
    assert redis_store.namespace == "LITESTAR"
    assert redis_store._make_key("foo") == "LITESTAR:foo"


def test_redis_with_namespace(redis_store: RedisStore) -> None:
    namespaced_test = redis_store.with_namespace("TEST")
    namespaced_test_foo = namespaced_test.with_namespace("FOO")
    assert namespaced_test.namespace == "LITESTAR_TEST"
    assert namespaced_test_foo.namespace == "LITESTAR_TEST_FOO"
    assert namespaced_test._redis is redis_store._redis


def test_redis_namespace_explicit_none(redis_client: AsyncRedis) -> None:
    assert RedisStore.with_client(url="redis://127.0.0.1", namespace=None).namespace is None
    assert RedisStore(redis=redis_client, namespace=None).namespace is None


async def test_file_init_directory(file_store: FileStore) -> None:
    shutil.rmtree(file_store.path)
    await file_store.set("foo", b"bar")


async def test_file_path(file_store: FileStore) -> None:
    await file_store.set("foo", b"bar")

    assert await (file_store.path / "foo").exists()


def test_file_with_namespace(file_store: FileStore) -> None:
    namespaced = file_store.with_namespace("foo")
    assert namespaced.path == file_store.path / "foo"


@pytest.mark.parametrize("invalid_char", string.punctuation)
def test_file_with_namespace_invalid_namespace_char(file_store: FileStore, invalid_char: str) -> None:
    with pytest.raises(ValueError):
        file_store.with_namespace(f"foo{invalid_char}")


@pytest.fixture(params=["redis_store", "file_store"])
def namespaced_store(request: FixtureRequest) -> NamespacedStore:
    return cast("NamespacedStore", request.getfixturevalue(request.param))


async def test_namespaced_store_get_set(namespaced_store: NamespacedStore) -> None:
    foo_namespaced = namespaced_store.with_namespace("foo")
    await namespaced_store.set("bar", b"litestar namespace")
    await foo_namespaced.set("bar", b"foo namespace")

    assert await namespaced_store.get("bar") == b"litestar namespace"
    assert await foo_namespaced.get("bar") == b"foo namespace"


async def test_namespaced_store_does_not_propagate_up(namespaced_store: NamespacedStore) -> None:
    foo_namespace = namespaced_store.with_namespace("FOO")
    await foo_namespace.set("foo", b"foo-value")
    await namespaced_store.set("bar", b"bar-value")

    await foo_namespace.delete_all()

    assert await foo_namespace.get("foo") is None
    assert await namespaced_store.get("bar") == b"bar-value"


async def test_namespaced_store_delete_all_propagates_down(namespaced_store: NamespacedStore) -> None:
    foo_namespace = namespaced_store.with_namespace("FOO")
    await foo_namespace.set("foo", b"foo-value")
    await namespaced_store.set("bar", b"bar-value")

    await namespaced_store.delete_all()

    assert await foo_namespace.get("foo") is None
    assert await namespaced_store.get("bar") is None


@pytest.mark.usefixtures("patch_storage_obj_frozen_datetime")
@pytest.mark.parametrize("store_fixture", ["memory_store", "file_store"])
async def test_memory_delete_expired(
    store_fixture: str, request: FixtureRequest, frozen_datetime: FrozenDateTimeFactory
) -> None:
    store = request.getfixturevalue(store_fixture)

    expect_expired: list[str] = []
    expect_not_expired: list[str] = []
    for i in range(10):
        key = f"key-{i}"
        expires_in = 0.001 if i % 2 == 0 else None
        await store.set(key, b"value", expires_in=expires_in)
        (expect_expired if expires_in else expect_not_expired).append(key)

    frozen_datetime.tick(1)
    await store.delete_expired()

    for key in expect_expired:
        assert await store.get(key) is None

    for key in expect_not_expired:
        assert await store.get(key) is not None


def test_registry_get(memory_store: MemoryStore) -> None:
    default_factory = MagicMock()
    default_factory.return_value = memory_store
    registry = StoreRegistry(default_factory=default_factory)
    default_factory.reset_mock()

    assert registry.get("foo") is memory_store
    assert registry.get("foo") is memory_store
    assert "foo" in registry._stores
    default_factory.assert_called_once_with("foo")


def test_registry_register(memory_store: MemoryStore) -> None:
    registry = StoreRegistry()

    registry.register("foo", memory_store)

    assert registry.get("foo") is memory_store


def test_registry_register_exist_raises(memory_store: MemoryStore) -> None:
    registry = StoreRegistry({"foo": memory_store})

    with pytest.raises(ValueError):
        registry.register("foo", memory_store)


def test_registry_register_exist_override(memory_store: MemoryStore) -> None:
    registry = StoreRegistry({"foo": memory_store})

    registry.register("foo", memory_store, allow_override=True)
    assert registry.get("foo") is memory_store
