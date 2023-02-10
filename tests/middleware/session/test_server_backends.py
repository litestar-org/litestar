from secrets import token_hex
from typing import TYPE_CHECKING

import anyio
import pytest

from starlite.storage.memcached_backend import MemcachedStorageBackend
from starlite.storage.redis_backend import RedisStorageBackend
from starlite.utils.serialization import encode_json

if TYPE_CHECKING:
    from starlite.middleware.session.server_side import ServerSideBackend


def generate_session_data() -> bytes:
    return encode_json({token_hex(): token_hex()})


@pytest.fixture
def session_data() -> bytes:
    return generate_session_data()


async def test_get_set(server_side_session_backend: "ServerSideBackend", session_data: bytes) -> None:
    await server_side_session_backend.set("foo", session_data)
    loaded = await server_side_session_backend.get("foo")

    assert loaded == session_data


async def test_get_set_multiple_returns_correct_identity(server_side_session_backend: "ServerSideBackend") -> None:
    foo_data = generate_session_data()
    bar_data = generate_session_data()
    await server_side_session_backend.set("foo", foo_data)
    await server_side_session_backend.set("bar", bar_data)

    loaded = await server_side_session_backend.get("foo")

    assert loaded == foo_data


async def test_delete(server_side_session_backend: "ServerSideBackend") -> None:
    await server_side_session_backend.set("foo", generate_session_data())
    await server_side_session_backend.set("bar", generate_session_data())

    await server_side_session_backend.delete("foo")

    assert not await server_side_session_backend.get("foo")
    assert await server_side_session_backend.get("bar")


async def test_delete_idempotence(server_side_session_backend: "ServerSideBackend", session_data: bytes) -> None:
    await server_side_session_backend.set("foo", session_data)

    await server_side_session_backend.delete("foo")
    await server_side_session_backend.delete("foo")  # ensure this doesn't raise an error


async def test_delete_all(server_side_session_backend: "ServerSideBackend") -> None:
    if isinstance(server_side_session_backend.storage, MemcachedStorageBackend):
        pytest.skip()

    await server_side_session_backend.set("foo", generate_session_data())
    await server_side_session_backend.set("bar", generate_session_data())

    await server_side_session_backend.delete_all()

    assert not await server_side_session_backend.get("foo")
    assert not await server_side_session_backend.get("bar")


async def test_max_age_expires(server_side_session_backend: "ServerSideBackend", session_data: bytes) -> None:
    expiry = 0.01 if not isinstance(server_side_session_backend.storage, RedisStorageBackend) else 1
    server_side_session_backend.config.max_age = expiry
    await server_side_session_backend.set("foo", session_data)
    await anyio.sleep(expiry + 0.01)

    assert not await server_side_session_backend.get("foo")
