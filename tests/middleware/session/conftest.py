import os
import secrets
from typing import TYPE_CHECKING, Any, AsyncGenerator, Generator, cast

import fakeredis.aioredis  # type: ignore
import py  # type: ignore
import pytest
from pydantic import SecretBytes
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

from starlite.middleware.session import SessionMiddleware
from starlite.middleware.session.base import (
    BaseBackendConfig,
    BaseSessionBackend,
    ServerSideBackend,
)
from starlite.middleware.session.cookie_backend import (
    CookieBackend,
    CookieBackendConfig,
)
from starlite.middleware.session.file_backend import FileBackend, FileBackendConfig
from starlite.middleware.session.memcached_backend import (
    MemcachedBackend,
    MemcachedBackendConfig,
)
from starlite.middleware.session.memory_backend import (
    MemoryBackend,
    MemoryBackendConfig,
)
from starlite.middleware.session.redis_backend import RedisBackend, RedisBackendConfig
from starlite.middleware.session.sqlalchemy_backend import (
    AsyncSQLAlchemyBackend,
    SQLAlchemyBackend,
    SQLAlchemyBackendConfig,
    create_session_model,
)
from starlite.plugins.sql_alchemy import (
    SQLAlchemyConfig,
    SQLAlchemyEngineConfig,
    SQLAlchemyPlugin,
)
from tests.fake_memcached import FakeAsyncMemcached

if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


Base = declarative_base()
SQLASessionModel = create_session_model(Base)


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


@pytest.fixture
def cookie_backend_config() -> CookieBackendConfig:
    return CookieBackendConfig(secret=SecretBytes(os.urandom(16)))


@pytest.fixture()
def cookie_session_backend(cookie_backend_config: CookieBackendConfig) -> CookieBackend:
    return CookieBackend(config=cookie_backend_config)


@pytest.fixture
def memory_backend_config() -> MemoryBackendConfig:
    return MemoryBackendConfig()


@pytest.fixture
def file_backend_config(tmpdir: py.path.local) -> FileBackendConfig:
    return FileBackendConfig(storage_path=tmpdir)


@pytest.fixture
def redis_backend_config() -> RedisBackendConfig:
    return RedisBackendConfig(redis=fakeredis.aioredis.FakeRedis())


engine_config = SQLAlchemyEngineConfig(connect_args={"check_same_thread": False}, poolclass=StaticPool)


@pytest.fixture
def sqlalchemy_backend_config() -> Generator[SQLAlchemyBackendConfig, None, None]:
    config = SQLAlchemyConfig(
        connection_string="sqlite+pysqlite://",
        use_async_engine=False,
        engine_config=engine_config,
    )
    Base.metadata.create_all(config.engine)  # type: ignore
    yield SQLAlchemyBackendConfig(plugin=SQLAlchemyPlugin(config=config), model=SQLASessionModel)
    Base.metadata.drop_all(config.engine)  # type: ignore


@pytest.fixture
async def async_sqlalchemy_backend_config() -> AsyncGenerator[SQLAlchemyBackendConfig, None]:
    config = SQLAlchemyConfig(connection_string="sqlite+aiosqlite://", engine_config=engine_config)
    async with config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)  # pyright: ignore
    yield SQLAlchemyBackendConfig(plugin=SQLAlchemyPlugin(config=config), model=SQLASessionModel)
    async with config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.drop_all)  # pyright: ignore


@pytest.fixture
def memcached_backend_config() -> MemcachedBackendConfig:
    return MemcachedBackendConfig(memcached=FakeAsyncMemcached())


@pytest.fixture
def memory_session_backend(memory_backend_config: MemoryBackendConfig) -> MemoryBackend:
    return MemoryBackend(config=memory_backend_config)


@pytest.fixture
def file_session_backend(file_backend_config: FileBackendConfig) -> FileBackend:
    return FileBackend(config=file_backend_config)


@pytest.fixture
def redis_session_backend(redis_backend_config: RedisBackendConfig) -> RedisBackend:
    return RedisBackend(config=redis_backend_config)


@pytest.fixture
def memcached_session_backend(memcached_backend_config: MemcachedBackendConfig) -> MemcachedBackend:
    return MemcachedBackend(config=memcached_backend_config)


@pytest.fixture
def sqlalchemy_session_backend(sqlalchemy_backend_config: SQLAlchemyBackendConfig) -> SQLAlchemyBackend:
    return SQLAlchemyBackend(config=sqlalchemy_backend_config)


@pytest.fixture
async def async_sqlalchemy_session_backend(
    async_sqlalchemy_backend_config: SQLAlchemyBackendConfig,
) -> AsyncSQLAlchemyBackend:
    return AsyncSQLAlchemyBackend(config=async_sqlalchemy_backend_config)


@pytest.fixture(
    params=[
        pytest.param("cookie_backend_config", id="cookie"),
        pytest.param("memory_backend_config", id="memory"),
        pytest.param("file_backend_config", id="file"),
        pytest.param("redis_backend_config", id="redis"),
        pytest.param("memcached_backend_config", id="memcached"),
        pytest.param("sqlalchemy_backend_config", id="sqlalchemy"),
        pytest.param("async_sqlalchemy_backend_config", id="sqlalchemy-async"),
    ]
)
def session_backend_config(request: pytest.FixtureRequest) -> BaseBackendConfig:
    return cast("BaseBackendConfig", request.getfixturevalue(request.param))


@pytest.fixture(
    params=[
        pytest.param("cookie_session_backend", id="cookie"),
        pytest.param("memory_session_backend", id="memory"),
        pytest.param("file_session_backend", id="file"),
        pytest.param("redis_session_backend", id="redis"),
        pytest.param("memcached_session_backend", id="memcached"),
        pytest.param("sqlalchemy_session_backend", id="sqlalchemy"),
        pytest.param("async_sqlalchemy_session_backend", id="sqlalchemy-async"),
    ]
)
def session_backend(request: pytest.FixtureRequest) -> BaseSessionBackend:
    return cast("BaseSessionBackend", request.getfixturevalue(request.param))


@pytest.fixture(
    params=[
        pytest.param("memory_session_backend", id="memory"),
        pytest.param("file_session_backend", id="file"),
        pytest.param("redis_session_backend", id="redis"),
        pytest.param("memcached_session_backend", id="memcached"),
        pytest.param("sqlalchemy_session_backend", id="sqlalchemy"),
        pytest.param("async_sqlalchemy_session_backend", id="sqlalchemy-async"),
    ]
)
def server_side_backend(request: pytest.FixtureRequest) -> ServerSideBackend:
    return cast("ServerSideBackend", request.getfixturevalue(request.param))


@pytest.fixture
def session_middleware(session_backend: BaseSessionBackend) -> SessionMiddleware[Any]:
    return SessionMiddleware(app=mock_asgi_app, backend=session_backend)


@pytest.fixture
def cookie_session_middleware(cookie_session_backend: CookieBackend) -> SessionMiddleware[CookieBackend]:
    return SessionMiddleware(app=mock_asgi_app, backend=cookie_session_backend)


@pytest.fixture()
def session_test_cookies(cookie_session_backend: CookieBackend) -> str:
    # Put random data. If you are also handling session management then use session_middleware fixture and create
    # session cookies with your own data.
    _session = {"key": secrets.token_hex(16)}
    return "; ".join(
        f"session-{i}={serialize.decode('utf-8')}"
        for i, serialize in enumerate(cookie_session_backend.dump_data(_session))
    )
