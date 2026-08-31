from __future__ import annotations

import asyncio
import math
import shutil
import string
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from _pytest.fixtures import FixtureRequest
from pytest_lazy_fixtures import lf
from pytest_mock import MockerFixture
from time_machine import Traveller

from litestar.exceptions import ImproperlyConfiguredException
from litestar.stores.file import FileStore
from litestar.stores.memory import MemoryStore
from litestar.stores.redis import RedisStore, RedisStoreNamespaceStrategy
from litestar.stores.registry import StoreRegistry
from litestar.stores.valkey import ValkeyStore

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from valkey.asyncio import Valkey

    from litestar.stores.base import NamespacedStore, Store


@pytest.fixture()
def mock_redis() -> None:
    patch("litestar.Store.redis_backend.Redis")


@pytest.fixture()
def mock_valkey() -> None:
    patch("litestar.Store.valkey_backend.Valkey")


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


async def test_expires(store: Store, frozen_datetime: Traveller) -> None:
    await store.set("foo", b"bar", expires_in=1)

    frozen_datetime.shift(2)
    if isinstance(store, RedisStore):
        # shifting time does not affect the Redis instance
        # this is done to emulate auto-expiration
        if store.namespace_strategy is RedisStoreNamespaceStrategy.HASH:
            await store._execute_command("HEXPIRE", store._make_hash_key(), 0, "FIELDS", 1, "foo")
        else:
            await store._redis.expire(f"{store.namespace}:foo", 0)
    if isinstance(store, ValkeyStore):
        await store._valkey.expire(f"{store.namespace}:foo", 0)

    stored_value = await store.get("foo")

    assert stored_value is None


@pytest.mark.flaky(reruns=5)
@pytest.mark.parametrize("renew_for", [10, timedelta(seconds=10)])
async def test_get_and_renew(store: Store, renew_for: int | timedelta, frozen_datetime: Traveller) -> None:
    if isinstance(store, (RedisStore, ValkeyStore)):
        pytest.skip()

    await store.set("foo", b"bar", expires_in=1)
    await store.get("foo", renew_for=renew_for)

    frozen_datetime.shift(2)

    stored_value = await store.get("foo")

    assert stored_value is not None


@pytest.mark.flaky(reruns=5)
@pytest.mark.parametrize("renew_for", [10, timedelta(seconds=10)])
@pytest.mark.parametrize("redis_backend", [lf("redis_store"), lf("redis_hash_store")])
@pytest.mark.xdist_group("redis")
async def test_get_and_renew_redis(redis_backend: RedisStore, renew_for: int | timedelta) -> None:
    # we can't sleep() in frozen datetime, and frozen datetime doesn't affect the redis
    # instance, so we test this separately
    await redis_backend.set("foo", b"bar", expires_in=1)
    await redis_backend.get("foo", renew_for=renew_for)

    await asyncio.sleep(1.1)

    stored_value = await redis_backend.get("foo")

    assert stored_value is not None


@pytest.mark.flaky(reruns=5)
@pytest.mark.parametrize("renew_for", [10, timedelta(seconds=10)])
@pytest.mark.xdist_group("valkey")
async def test_get_and_renew_valkey(valkey_store: ValkeyStore, renew_for: int | timedelta) -> None:
    # we can't sleep() in frozen datetime, and frozen datetime doesn't affect the redis
    # instance, so we test this separately
    await valkey_store.set("foo", b"bar", expires_in=1)
    await valkey_store.get("foo", renew_for=renew_for)

    await asyncio.sleep(1.1)

    stored_value = await valkey_store.get("foo")

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


async def test_expires_in(store: Store, frozen_datetime: Traveller) -> None:
    if not isinstance(store, (RedisStore, ValkeyStore)):
        pytest.xfail("bug in FileStore and MemoryStore")

    assert await store.expires_in("foo") is None

    await store.set("foo", "bar")
    assert await store.expires_in("foo") == -1

    await store.set("foo", "bar", expires_in=10)
    expiration = await store.expires_in("foo")
    assert expiration is not None
    assert math.ceil(expiration / 10) == 1

    if isinstance(store, RedisStore):
        if store.namespace_strategy is RedisStoreNamespaceStrategy.HASH:
            await store._execute_command("HEXPIRE", store._make_hash_key(), 0, "FIELDS", 1, "foo")
        else:
            await store._redis.expire(f"{store.namespace}:foo", 0)
    elif isinstance(store, ValkeyStore):
        await store._valkey.expire(f"{store.namespace}:foo", 0)
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
    assert backend.namespace_strategy is RedisStoreNamespaceStrategy.KEYS


async def test_redis_keys_strategy_does_not_query_server_version() -> None:
    redis = MagicMock()
    redis.info = AsyncMock()
    store = RedisStore(redis=redis)

    await store.__aenter__()

    assert store._resolved_namespace_strategy is RedisStoreNamespaceStrategy.KEYS
    redis.info.assert_not_awaited()


@pytest.mark.parametrize(
    ("version", "expected_strategy"),
    [
        ("7.2.9", RedisStoreNamespaceStrategy.KEYS),
        ("7.4.0", RedisStoreNamespaceStrategy.HASH),
        ("8.0.0", RedisStoreNamespaceStrategy.HASH),
    ],
)
async def test_redis_auto_strategy_uses_server_version(
    version: str, expected_strategy: RedisStoreNamespaceStrategy
) -> None:
    redis = MagicMock()
    redis.info = AsyncMock(return_value={"redis_version": version})
    store = RedisStore(redis=redis, namespace_strategy=RedisStoreNamespaceStrategy.AUTO)

    await store.__aenter__()

    assert store._resolved_namespace_strategy is expected_strategy
    redis.info.assert_awaited_once_with("server")


async def test_redis_hash_strategy_rejects_unsupported_server() -> None:
    redis = MagicMock()
    redis.info = AsyncMock(return_value={"redis_version": "7.2.9"})
    store = RedisStore(redis=redis, namespace_strategy=RedisStoreNamespaceStrategy.HASH)

    with pytest.raises(ImproperlyConfiguredException, match="requires Redis 7.4 or later"):
        await store.__aenter__()


@pytest.mark.parametrize("namespace_strategy", [RedisStoreNamespaceStrategy.HASH, RedisStoreNamespaceStrategy.AUTO])
async def test_redis_hash_strategy_resolves_after_adding_namespace(
    namespace_strategy: RedisStoreNamespaceStrategy,
) -> None:
    redis = MagicMock()
    redis.info = AsyncMock(return_value={"redis_version": "8.0.0"})
    root_store = RedisStore(redis=redis, namespace=None, namespace_strategy=namespace_strategy)

    await root_store.__aenter__()
    namespaced_store = root_store.with_namespace("child")
    await namespaced_store.__aenter__()
    nested_store = namespaced_store.with_namespace("nested")

    assert root_store._resolved_namespace_strategy is RedisStoreNamespaceStrategy.KEYS
    assert namespaced_store._resolved_namespace_strategy is RedisStoreNamespaceStrategy.HASH
    assert nested_store.namespace_strategy is namespace_strategy
    assert nested_store._redis_version == namespaced_store._redis_version
    assert nested_store._resolved_namespace_strategy is RedisStoreNamespaceStrategy.HASH
    redis.info.assert_awaited_once_with("server")


@patch("litestar.stores.valkey.Valkey")
@patch("litestar.stores.valkey.ConnectionPool.from_url")
def test_valkey_with_client_default(connection_pool_from_url_mock: Mock, mock_valkey: Mock) -> None:
    backend = ValkeyStore.with_client()
    connection_pool_from_url_mock.assert_called_once_with(
        url="valkey://localhost:6379", db=None, port=None, username=None, password=None, decode_responses=False
    )
    mock_valkey.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._valkey is mock_valkey.return_value


@patch("litestar.stores.redis.Redis")
@patch("litestar.stores.redis.ConnectionPool.from_url")
def test_redis_with_non_default(connection_pool_from_url_mock: Mock, mock_redis: Mock) -> None:
    url = "redis://localhost"
    db = 2
    port = 1234
    username = "user"
    password = "password"
    backend = RedisStore.with_client(
        url=url,
        db=db,
        port=port,
        username=username,
        password=password,
        namespace_strategy=RedisStoreNamespaceStrategy.HASH,
    )
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=db, port=port, username=username, password=password, decode_responses=False
    )
    mock_redis.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._redis is mock_redis.return_value
    assert backend.namespace_strategy is RedisStoreNamespaceStrategy.HASH


@patch("litestar.stores.redis.Redis")
@patch("litestar.stores.redis.ConnectionPool.from_url")
async def test_redis_set_with_expires_in_and_keep_ttl_raises(
    connection_pool_from_url_mock: Mock, mock_redis: Mock
) -> None:
    """Test that setting both expires_in and keep_ttl raises ValueError."""
    store = RedisStore.with_client()

    with pytest.raises(ValueError, match="Cannot set both 'expires_in' and 'keep_ttl'"):
        await store.set("key", b"value", expires_in=60, keep_ttl=True)  # type: ignore[call-overload]


@pytest.mark.xdist_group("redis")
@pytest.mark.parametrize("redis_backend", [lf("redis_store"), lf("redis_hash_store")])
async def test_redis_set_with_keep_ttl(redis_backend: RedisStore) -> None:
    """Test that keep_ttl=True preserves the existing TTL."""
    # Set key with initial TTL
    await redis_backend.set("foo", b"bar", expires_in=100)
    initial_ttl = await redis_backend.expires_in("foo")
    assert initial_ttl is not None and initial_ttl > 0

    # Update value with keep_ttl=True - TTL should be preserved
    await redis_backend.set("foo", b"updated", keep_ttl=True)
    new_ttl = await redis_backend.expires_in("foo")

    assert new_ttl is not None and new_ttl > 0
    assert await redis_backend.get("foo") == b"updated"


@pytest.mark.xdist_group("redis")
async def test_redis_hash_set_without_expiry_discards_ttl(redis_hash_store: RedisStore) -> None:
    await redis_hash_store.set("foo", b"bar", expires_in=100)

    await redis_hash_store.set("foo", b"updated")

    assert await redis_hash_store.expires_in("foo") == -1
    assert await redis_hash_store.get("foo", renew_for=60) == b"updated"
    assert await redis_hash_store.expires_in("foo") == -1


@pytest.mark.xdist_group("redis")
async def test_redis_hash_strategy_74_compatibility(redis_client: Redis) -> None:
    store = RedisStore(redis=redis_client, namespace_strategy=RedisStoreNamespaceStrategy.HASH)
    store._redis_version = (7, 4)
    store._resolved_namespace_strategy = RedisStoreNamespaceStrategy.HASH

    await store.set("expiring", b"initial", expires_in=60)
    await store.set("expiring", b"updated", keep_ttl=True)
    assert await store.get("expiring", renew_for=120) == b"updated"
    expires_in = await store.expires_in("expiring")
    assert expires_in is not None and expires_in > 60

    await store.set("persistent", b"value")
    assert await store.get("persistent", renew_for=60) == b"value"
    assert await store.expires_in("persistent") == -1


@patch("litestar.stores.valkey.Valkey")
@patch("litestar.stores.valkey.ConnectionPool.from_url")
def test_valkey_with_non_default(connection_pool_from_url_mock: Mock, mock_valkey: Mock) -> None:
    url = "valkey://localhost"
    db = 2
    port = 1234
    username = "user"
    password = "password"
    backend = ValkeyStore.with_client(url=url, db=db, port=port, username=username, password=password)
    connection_pool_from_url_mock.assert_called_once_with(
        url=url, db=db, port=port, username=username, password=password, decode_responses=False
    )
    mock_valkey.assert_called_once_with(connection_pool=connection_pool_from_url_mock.return_value)
    assert backend._valkey is mock_valkey.return_value


@pytest.mark.xdist_group("redis")
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


@pytest.mark.xdist_group("redis")
async def test_redis_hash_namespace_uses_one_key_and_deletes_children(redis_hash_store: RedisStore) -> None:
    child_store = redis_hash_store.with_namespace("child")
    independent_store = RedisStore(
        redis=redis_hash_store._redis,
        namespace="LITESTAR2",
        namespace_strategy=RedisStoreNamespaceStrategy.HASH,
    )
    await redis_hash_store._redis.set("test_key", b"test_value")
    await redis_hash_store._redis.set("LITESTAR:legacy", b"legacy_value")
    await redis_hash_store._redis.set("LITESTAR_unrelated", b"unrelated_value")
    await redis_hash_store.set("root", b"root_value")
    await child_store.set("child", b"child_value")
    await independent_store.set("independent", b"independent_value")

    root_hash_key = redis_hash_store._make_hash_key()
    child_hash_key = child_store._make_hash_key()
    assert await redis_hash_store._execute_command("TYPE", root_hash_key) == b"hash"
    assert await redis_hash_store._redis.hget(root_hash_key, "root") == b"root_value"
    assert await redis_hash_store._redis.hget(child_hash_key, "child") == b"child_value"
    assert await redis_hash_store._redis.get("LITESTAR:root") is None

    await redis_hash_store.delete_all()

    assert await redis_hash_store._redis.exists(root_hash_key) == 0
    assert await redis_hash_store._redis.exists(child_hash_key) == 0
    assert await redis_hash_store._redis.get("test_key") == b"test_value"
    assert await redis_hash_store._redis.get("LITESTAR:legacy") == b"legacy_value"
    assert await redis_hash_store._redis.get("LITESTAR_unrelated") == b"unrelated_value"
    assert await independent_store.get("independent") == b"independent_value"


@pytest.mark.xdist_group("redis")
async def test_redis_hash_namespace_with_glob_characters_is_isolated(redis_client: Redis) -> None:
    store = RedisStore(
        redis=redis_client,
        namespace="ROOT:*?[]",
        namespace_strategy=RedisStoreNamespaceStrategy.HASH,
    )
    child_store = store.with_namespace("child")
    independent_store = RedisStore(
        redis=redis_client,
        namespace="ROOT:X",
        namespace_strategy=RedisStoreNamespaceStrategy.HASH,
    )
    await child_store.set("item", b"child_value")
    await independent_store.set("item", b"independent_value")

    await store.delete_all()

    assert await child_store.get("item") is None
    assert await independent_store.get("item") == b"independent_value"


@pytest.mark.xdist_group("valkey")
async def test_valkey_delete_all(valkey_store: ValkeyStore) -> None:
    await valkey_store._valkey.set("test_key", b"test_value")

    keys = []
    for i in range(10):
        key = f"key-{i}"
        keys.append(key)
        await valkey_store.set(key, b"value", expires_in=10 if i % 2 else None)

    await valkey_store.delete_all()

    for key in keys:
        assert await valkey_store.get(key) is None

    stored_value = await valkey_store._valkey.get("test_key")
    assert stored_value == b"test_value"  # check it doesn't delete other values


@pytest.mark.xdist_group("redis")
async def test_redis_delete_all_no_namespace_raises(redis_client: Redis) -> None:
    redis_store = RedisStore(redis=redis_client, namespace=None)

    with pytest.raises(ImproperlyConfiguredException):
        await redis_store.delete_all()


@pytest.mark.xdist_group("valkey")
async def test_valkey_delete_all_no_namespace_raises(valkey_client: Valkey) -> None:
    valkey_store = ValkeyStore(valkey=valkey_client, namespace=None)

    with pytest.raises(ImproperlyConfiguredException):
        await valkey_store.delete_all()


@pytest.mark.xdist_group("redis")
def test_redis_namespaced_key(redis_store: RedisStore) -> None:
    assert redis_store.namespace == "LITESTAR"
    assert redis_store._make_key("foo") == "LITESTAR:foo"


@pytest.mark.xdist_group("valkey")
def test_valkey_namespaced_key(valkey_store: ValkeyStore) -> None:
    assert valkey_store.namespace == "LITESTAR"
    assert valkey_store._make_key("foo") == "LITESTAR:foo"


@pytest.mark.xdist_group("redis")
def test_redis_with_namespace(redis_store: RedisStore) -> None:
    namespaced_test = redis_store.with_namespace("TEST")
    namespaced_test_foo = namespaced_test.with_namespace("FOO")
    assert namespaced_test.namespace == "LITESTAR_TEST"
    assert namespaced_test_foo.namespace == "LITESTAR_TEST_FOO"
    assert namespaced_test._redis is redis_store._redis


@pytest.mark.xdist_group("valkey")
def test_valkey_with_namespace(valkey_store: ValkeyStore) -> None:
    namespaced_test = valkey_store.with_namespace("TEST")
    namespaced_test_foo = namespaced_test.with_namespace("FOO")
    assert namespaced_test.namespace == "LITESTAR_TEST"
    assert namespaced_test_foo.namespace == "LITESTAR_TEST_FOO"
    assert namespaced_test._valkey is valkey_store._valkey


@pytest.mark.xdist_group("redis")
def test_redis_namespace_explicit_none(redis_client: Redis) -> None:
    assert RedisStore.with_client(url="redis://127.0.0.1", namespace=None).namespace is None
    assert RedisStore(redis=redis_client, namespace=None).namespace is None


@pytest.mark.xdist_group("valkey")
def test_valkey_namespace_explicit_none(valkey_client: Valkey) -> None:
    assert ValkeyStore.with_client(url="redis://127.0.0.1", namespace=None).namespace is None
    assert ValkeyStore(valkey=valkey_client, namespace=None).namespace is None


async def test_file_init_directory(file_store: FileStore) -> None:
    shutil.rmtree(file_store.path)
    await file_store.set("foo", b"bar")


async def test_file_init_subdirectory(file_store_create_directories: FileStore) -> None:
    file_store = file_store_create_directories
    async with file_store:
        await file_store.set("foo", b"bar")


async def test_file_init_subdirectory_negative(file_store_create_directories_flag_false: FileStore) -> None:
    file_store = file_store_create_directories_flag_false
    async with file_store:
        with pytest.raises(FileNotFoundError):
            await file_store.set("foo", b"bar")


async def test_file_path(file_store: FileStore) -> None:
    await file_store.set("foo", b"bar")

    assert await (file_store.path / file_store._path_from_key("foo")).exists()


@pytest.mark.parametrize(
    "key_one, key_two",
    [
        ("foo/bar", "foobar"),  # os path separator
        ("foo\\bar", "foobar"),  # os path separator
        ("foo/../bar", "foobar"),  # directory traversal
        ("fook-", "fook45"),  # char encoding
        ("fooK", "fooK"),  # unicode confusable (Kelvin symbol vs K) # noqa: RUF001
        ("foo\\n", "foo92n"),  # a newline?
        ("foo\r\nbar", "foobar"),  # a CRLF
        ("foo\u0000bar", "foobar"),  # NUL byte stripping
        ("Foo", "foo"),  # lowercasing
        ("fooß", "fooss"),  # ß folding (relevant in de_DE)
        ("fooß", "fooẞ"),  # lower an uppercase ß
        ("café", "cafe\u0301"),  # composed vs decomposed é
        ("Å", "A\u030a"),  # ring-above normalization
        ("Å", "Å"),  # Angstrom sign vs A-ring
        ("fooΟ", "fooO"),  # greek omicron vs latin O  # noqa: RUF001
        ("fooа", "fooa"),  # cyrillic a vs Latin a  # noqa: RUF001
        ("foo\u00a0bar", "foo bar"),  # non-breaking space vs space
        ("foo\tbar", "foo bar"),  # tab normalization
        ("foo%2Fbar", "foo/bar"),  # percent-encoded slash
        ("foo%2e%2e%2fbar", "foo/../bar"),  # encoded traversal
        ("a" * 255 + "X", "a" * 255 + "Y"),  # filesystem length truncation
    ],
)
async def test_file_normalize_key(file_store: FileStore, key_one: str, key_two: str) -> None:
    await file_store.set(key_one, b"one")
    await file_store.set(key_two, b"two")

    assert await file_store.get(key_one) == b"one"
    assert await file_store.get(key_two) == b"two"


def test_file_with_namespace(file_store: FileStore) -> None:
    namespaced = file_store.with_namespace("foo")
    assert namespaced.path == file_store.path / "foo"


@pytest.mark.parametrize("invalid_char", string.punctuation)
def test_file_with_namespace_invalid_namespace_char(file_store: FileStore, invalid_char: str) -> None:
    with pytest.raises(ValueError):
        file_store.with_namespace(f"foo{invalid_char}")


@pytest.fixture(
    params=[
        pytest.param("redis_store", marks=pytest.mark.xdist_group("redis")),
        pytest.param("redis_hash_store", marks=pytest.mark.xdist_group("redis")),
        pytest.param("valkey_store", marks=pytest.mark.xdist_group("valkey")),
        "file_store",
    ]
)
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


@pytest.mark.parametrize("store_fixture", ["memory_store", "file_store"])
async def test_memory_delete_expired(store_fixture: str, request: FixtureRequest, frozen_datetime: Traveller) -> None:
    store = request.getfixturevalue(store_fixture)

    expect_expired: list[str] = []
    expect_not_expired: list[str] = []
    for i in range(10):
        key = f"key-{i}"
        expires_in = 0.001 if i % 2 == 0 else None
        await store.set(key, b"value", expires_in=expires_in)
        (expect_expired if expires_in else expect_not_expired).append(key)

    frozen_datetime.shift(1)
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


async def test_file_store_handle_rename_fail(file_store: FileStore, mocker: MockerFixture) -> None:
    mocker.patch("litestar.stores.file.os.replace", side_effect=OSError)
    mock_unlink = mocker.patch("litestar.stores.file.os.unlink")

    await file_store.set("foo", "bar")
    mock_unlink.assert_called_once()
    assert Path(mock_unlink.call_args_list[0].args[0]).with_suffix("") == file_store.path.joinpath(
        file_store._path_from_key("foo")
    )


@pytest.mark.xdist_group("redis")
async def test_redis_store_with_client_shutdown(redis_service: None) -> None:
    redis_store = RedisStore.with_client(url="redis://localhost:6397")
    assert await redis_store._redis.ping()
    # remove the private shutdown and the assert below fails
    # the check on connection is a mimic of https://github.com/redis/redis-py/blob/d529c2ad8d2cf4dcfb41bfd93ea68cfefd81aa66/tests/test_asyncio/test_connection_pool.py#L35-L39
    await redis_store._shutdown()
    assert not any(
        x.is_connected
        for x in redis_store._redis.connection_pool._available_connections
        + list(redis_store._redis.connection_pool._in_use_connections)
    )


@pytest.mark.xdist_group("valkey")
async def test_valkey_store_with_client_shutdown(valkey_service: None) -> None:
    valkey_store = ValkeyStore.with_client(url="valkey://localhost:6381")
    assert await valkey_store._valkey.ping()
    # remove the private shutdown and the assert below fails
    # the check on connection is a mimic of https://github.com/redis/redis-py/blob/d529c2ad8d2cf4dcfb41bfd93ea68cfefd81aa66/tests/test_asyncio/test_connection_pool.py#L35-L39
    await valkey_store._shutdown()
    assert not any(
        x.is_connected  # pyright: ignore[reportAttributeAccessIssue]
        for x in valkey_store._valkey.connection_pool._available_connections
        + list(valkey_store._valkey.connection_pool._in_use_connections)
    )
