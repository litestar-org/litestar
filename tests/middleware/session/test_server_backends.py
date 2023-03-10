from __future__ import annotations
from secrets import token_hex
from typing import TYPE_CHECKING

import anyio
import pytest

from starlite.exceptions import ImproperlyConfiguredException
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.serialization import encode_json

if TYPE_CHECKING:
    from starlite.middleware.session.server_side import ServerSideSessionBackend


def generate_session_data() -> bytes:
    return encode_json({token_hex(): token_hex()})


@pytest.fixture
def session_data() -> bytes:
    return generate_session_data()


async def test_get_set(server_side_session_backend: "ServerSideSessionBackend", session_data: bytes) -> None:
    await server_side_session_backend.set("foo", session_data)
    loaded = await server_side_session_backend.get("foo")

    assert loaded == session_data


async def test_get_renew_on_access(
    server_side_session_backend: "ServerSideSessionBackend", session_data: bytes
) -> None:
    server_side_session_backend.config.max_age = 1
    server_side_session_backend.config.renew_on_access = True

    await server_side_session_backend.set("foo", session_data)
    server_side_session_backend.config.max_age = 10

    await server_side_session_backend.get("foo")

    await anyio.sleep(1.01)

    assert await server_side_session_backend.get("foo") is not None


async def test_get_set_multiple_returns_correct_identity(
    server_side_session_backend: "ServerSideSessionBackend",
) -> None:
    foo_data = generate_session_data()
    bar_data = generate_session_data()
    await server_side_session_backend.set("foo", foo_data)
    await server_side_session_backend.set("bar", bar_data)

    loaded = await server_side_session_backend.get("foo")

    assert loaded == foo_data


async def test_delete(server_side_session_backend: "ServerSideSessionBackend") -> None:
    await server_side_session_backend.set("foo", generate_session_data())
    await server_side_session_backend.set("bar", generate_session_data())

    await server_side_session_backend.delete("foo")

    assert not await server_side_session_backend.get("foo")
    assert await server_side_session_backend.get("bar")


async def test_delete_idempotence(server_side_session_backend: "ServerSideSessionBackend", session_data: bytes) -> None:
    await server_side_session_backend.set("foo", session_data)

    await server_side_session_backend.delete("foo")
    await server_side_session_backend.delete("foo")  # ensure this doesn't raise an error


async def test_max_age_expires(server_side_session_backend: "ServerSideSessionBackend", session_data: bytes) -> None:
    server_side_session_backend.config.max_age = 1
    await server_side_session_backend.set("foo", session_data)
    await anyio.sleep(1)
    assert not await server_side_session_backend.get("foo")


@pytest.mark.parametrize(
    "key, should_raise",
    [
        ["", True],
        ["a", False],
        ["a" * 256, False],
        ["a" * 257, True],
    ],
)
def test_key_validation(server_side_session_backend: "ServerSideSessionBackend", key: str, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            ServerSideSessionConfig(key=key, storage=server_side_session_backend.storage)
    else:
        ServerSideSessionConfig(key=key, storage=server_side_session_backend.storage)


@pytest.mark.parametrize(
    "max_age, should_raise",
    [
        [0, True],
        [-1, True],
        [1, False],
        [100, False],
    ],
)
def test_max_age_validation(
    server_side_session_backend: "ServerSideSessionBackend", max_age: int, should_raise: bool
) -> None:
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            ServerSideSessionConfig(key="a", max_age=max_age, storage=server_side_session_backend.storage)
    else:
        ServerSideSessionConfig(key="a", max_age=max_age, storage=server_side_session_backend.storage)
