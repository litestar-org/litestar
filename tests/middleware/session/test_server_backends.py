import datetime
import shutil
from secrets import token_hex
from typing import TYPE_CHECKING

import anyio
import orjson
import pytest
import sqlalchemy as sa

from starlite.middleware.session.memcached_backend import MemcachedBackend
from starlite.middleware.session.redis_backend import RedisBackend
from starlite.middleware.session.sqlalchemy_backend import (
    AsyncSQLAlchemyBackend,
    SQLAlchemyBackend,
    SQLAlchemyBackendConfig,
)

if TYPE_CHECKING:
    from starlite.middleware.session.base import ServerSideBackend
    from starlite.middleware.session.file_backend import FileBackend


def generate_session_data() -> bytes:
    return orjson.dumps({token_hex(): token_hex()})


@pytest.fixture
def session_data() -> bytes:
    return generate_session_data()


async def test_get_set(server_side_backend: ServerSideBackend, session_data: bytes) -> None:
    await server_side_backend.set("foo", session_data)
    loaded = await server_side_backend.get("foo")

    assert loaded == session_data


async def test_get_set_multiple_returns_correct_identity(server_side_backend: ServerSideBackend) -> None:
    foo_data = generate_session_data()
    bar_data = generate_session_data()
    await server_side_backend.set("foo", foo_data)
    await server_side_backend.set("bar", bar_data)

    loaded = await server_side_backend.get("foo")

    assert loaded == foo_data


async def test_delete(server_side_backend: ServerSideBackend) -> None:
    await server_side_backend.set("foo", generate_session_data())
    await server_side_backend.set("bar", generate_session_data())

    await server_side_backend.delete("foo")

    assert not await server_side_backend.get("foo")
    assert await server_side_backend.get("bar")


async def test_delete_idempotence(server_side_backend: ServerSideBackend, session_data: bytes) -> None:
    await server_side_backend.set("foo", session_data)

    await server_side_backend.delete("foo")
    await server_side_backend.delete("foo")  # ensure this doesn't raise an error


async def test_delete_all(server_side_backend: ServerSideBackend) -> None:
    if isinstance(server_side_backend, MemcachedBackend):
        pytest.skip()

    await server_side_backend.set("foo", generate_session_data())
    await server_side_backend.set("bar", generate_session_data())

    await server_side_backend.delete_all()

    assert not await server_side_backend.get("foo")
    assert not await server_side_backend.get("bar")


async def test_max_age_expires(server_side_backend: ServerSideBackend, session_data: bytes) -> None:
    expiry = 0.01 if not isinstance(server_side_backend, RedisBackend) else 1
    server_side_backend.config.max_age = expiry
    await server_side_backend.set("foo", session_data)
    await anyio.sleep(expiry + 0.01)

    assert not await server_side_backend.get("foo")


async def test_file_backend_init_directory(file_session_backend: FileBackend, session_data: bytes) -> None:
    shutil.rmtree(file_session_backend.path)
    await file_session_backend.set("foo", session_data)


async def test_file_backend_path(file_session_backend: FileBackend, session_data: bytes) -> None:
    await file_session_backend.set("foo", session_data)

    assert await (file_session_backend.path / "foo").exists()


async def test_load_file_not_found_returns_emtpy_session(
    file_session_backend: FileBackend, session_data: bytes
) -> None:
    await file_session_backend.set("foo", session_data)
    await (file_session_backend.path / "foo").unlink()

    assert not await file_session_backend.get("foo")


async def test_sqlalchemy_backend_delete_expired(sqlalchemy_session_backend: SQLAlchemyBackend) -> None:
    await sqlalchemy_session_backend.set("foo", generate_session_data())
    await sqlalchemy_session_backend.set("bar", generate_session_data())

    session = sqlalchemy_session_backend._create_sa_session()
    model = sqlalchemy_session_backend.config.model
    session.execute(
        sa.update(model)
        .where(model.session_id == "foo")
        .values(expires=datetime.datetime.utcnow().replace(tzinfo=None))
    )
    await sqlalchemy_session_backend.delete_expired()

    assert not await sqlalchemy_session_backend.get("foo")
    assert await sqlalchemy_session_backend.get("bar")


async def test_sqlalchemy_async_backend_delete_expired(
    async_sqlalchemy_session_backend: AsyncSQLAlchemyBackend,
) -> None:
    await async_sqlalchemy_session_backend.set("foo", generate_session_data())
    await async_sqlalchemy_session_backend.set("bar", generate_session_data())

    session = async_sqlalchemy_session_backend._create_sa_session()
    model = async_sqlalchemy_session_backend.config.model
    await session.execute(
        sa.update(model)
        .where(model.session_id == "foo")
        .values(expires=datetime.datetime.utcnow().replace(tzinfo=None))
    )
    await async_sqlalchemy_session_backend.delete_expired()

    assert not await async_sqlalchemy_session_backend.get("foo")
    assert await async_sqlalchemy_session_backend.get("bar")


def test_sqlalchemy_config_dynamic_backend(
    sqlalchemy_backend_config: SQLAlchemyBackendConfig, async_sqlalchemy_backend_config: SQLAlchemyBackendConfig
) -> None:
    assert sqlalchemy_backend_config._backend_class is SQLAlchemyBackend
    assert async_sqlalchemy_backend_config._backend_class is AsyncSQLAlchemyBackend
