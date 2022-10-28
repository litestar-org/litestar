import os
import pathlib
import sys
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Generator, Union, cast

import fakeredis.aioredis  # type: ignore
import py  # type: ignore
import pytest
from piccolo.conf.apps import Finder
from piccolo.table import create_db_tables, drop_db_tables
from pydantic import SecretBytes
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

from starlite.middleware.session import SessionMiddleware
from starlite.middleware.session.base import (
    BaseSessionBackend,
    ServerSideBackend,
    ServerSideSessionConfig,
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
from tests.mocks import FakeAsyncMemcached

if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


def pytest_generate_tests(metafunc: Callable) -> None:
    """Sets ENV variables for testing."""
    os.environ.update(PICCOLO_CONF="tests.piccolo_conf")


@pytest.fixture()
def template_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


@pytest.fixture()
async def scaffold_tortoise() -> AsyncGenerator:
    """Scaffolds Tortoise ORM and performs cleanup."""
    from tests.plugins.tortoise_orm import cleanup, init_tortoise

    await init_tortoise()
    yield
    await cleanup()


@pytest.fixture()
async def scaffold_piccolo() -> AsyncGenerator:
    """Scaffolds Piccolo ORM and performs cleanup."""
    TABLES = Finder().get_table_classes()
    await drop_db_tables(*TABLES)
    await create_db_tables(*TABLES)
    yield
    await drop_db_tables(*TABLES)


@pytest.fixture(
    params=[
        pytest.param("asyncio", id="asyncio"),
        pytest.param("trio", id="trio"),
    ]
)
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture()
def sqlalchemy_base() -> Any:
    return declarative_base()


@pytest.fixture()
def sqlalchemy_session_model(sqlalchemy_base: Any) -> Any:
    return create_session_model(sqlalchemy_base)


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


@pytest.fixture
def cookie_session_backend_config() -> CookieBackendConfig:
    return CookieBackendConfig(secret=SecretBytes(os.urandom(16)))


@pytest.fixture()
def cookie_session_backend(cookie_session_backend_config: CookieBackendConfig) -> CookieBackend:
    return CookieBackend(config=cookie_session_backend_config)


@pytest.fixture
def memory_session_backend_config() -> MemoryBackendConfig:
    return MemoryBackendConfig()


@pytest.fixture
def file_session_backend_config(tmpdir: py.path.local) -> FileBackendConfig:
    return FileBackendConfig(storage_path=tmpdir)


@pytest.fixture
def redis_session_backend_config() -> RedisBackendConfig:
    return RedisBackendConfig(redis=fakeredis.aioredis.FakeRedis())


engine_config = SQLAlchemyEngineConfig(connect_args={"check_same_thread": False}, poolclass=StaticPool)


@pytest.fixture
def sqlalchemy_session_backend_config(
    sqlalchemy_session_model: Any, sqlalchemy_base: Any
) -> Generator[SQLAlchemyBackendConfig, None, None]:
    config = SQLAlchemyConfig(
        connection_string="sqlite+pysqlite://",
        use_async_engine=False,
        engine_config=engine_config,
    )
    sqlalchemy_base.metadata.create_all(config.engine)
    yield SQLAlchemyBackendConfig(plugin=SQLAlchemyPlugin(config=config), model=sqlalchemy_session_model)
    sqlalchemy_base.metadata.drop_all(config.engine)


@pytest.fixture
async def async_sqlalchemy_session_backend_config(
    sqlalchemy_session_model: Any, sqlalchemy_base: Any
) -> AsyncGenerator[SQLAlchemyBackendConfig, None]:
    config = SQLAlchemyConfig(connection_string="sqlite+aiosqlite://", engine_config=engine_config)
    async with config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(sqlalchemy_base.metadata.create_all)  # pyright: ignore
    yield SQLAlchemyBackendConfig(plugin=SQLAlchemyPlugin(config=config), model=sqlalchemy_session_model)
    async with config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(sqlalchemy_base.metadata.drop_all)  # pyright: ignore


@pytest.fixture
def memcached_session_backend_config() -> MemcachedBackendConfig:
    return MemcachedBackendConfig(memcached=FakeAsyncMemcached())


@pytest.fixture
def memory_session_backend(memory_session_backend_config: MemoryBackendConfig) -> MemoryBackend:
    return MemoryBackend(config=memory_session_backend_config)


@pytest.fixture
def file_session_backend(file_session_backend_config: FileBackendConfig) -> FileBackend:
    return FileBackend(config=file_session_backend_config)


@pytest.fixture
def redis_session_backend(redis_session_backend_config: RedisBackendConfig) -> RedisBackend:
    return RedisBackend(config=redis_session_backend_config)


@pytest.fixture
def memcached_session_backend(memcached_session_backend_config: MemcachedBackendConfig) -> MemcachedBackend:
    return MemcachedBackend(config=memcached_session_backend_config)


@pytest.fixture
def sqlalchemy_session_backend(sqlalchemy_session_backend_config: SQLAlchemyBackendConfig) -> SQLAlchemyBackend:
    return SQLAlchemyBackend(config=sqlalchemy_session_backend_config)


@pytest.fixture
async def async_sqlalchemy_session_backend(
    async_sqlalchemy_session_backend_config: SQLAlchemyBackendConfig,
) -> AsyncSQLAlchemyBackend:
    return AsyncSQLAlchemyBackend(config=async_sqlalchemy_session_backend_config)


@pytest.fixture(
    params=[
        pytest.param("cookie_session_backend_config", id="cookie"),
        pytest.param("memory_session_backend_config", id="memory"),
        pytest.param("file_session_backend_config", id="file"),
        pytest.param("redis_session_backend_config", id="redis"),
        pytest.param("memcached_session_backend_config", id="memcached"),
        pytest.param("sqlalchemy_session_backend_config", id="sqlalchemy"),
        pytest.param("async_sqlalchemy_session_backend_config", id="sqlalchemy-async"),
    ]
)
def session_backend_config(request: pytest.FixtureRequest) -> Union[ServerSideSessionConfig, CookieBackendConfig]:
    return cast("Union[ServerSideSessionConfig, CookieBackendConfig]", request.getfixturevalue(request.param))


@pytest.fixture(
    params=[
        pytest.param("cookie_session_backend_config", id="cookie"),
        pytest.param("memory_session_backend_config", id="memory"),
        pytest.param("file_session_backend_config", id="file"),
        pytest.param("redis_session_backend_config", id="redis"),
        pytest.param("memcached_session_backend_config", id="memcached"),
        pytest.param("sqlalchemy_session_backend_config", id="sqlalchemy"),
        pytest.param("async_sqlalchemy_session_backend_config", id="sqlalchemy-async"),
    ]
)
def session_backend_config_async_safe(
    request: pytest.FixtureRequest,
) -> Union[ServerSideSessionConfig, CookieBackendConfig]:
    if sys.version_info < (3, 9) and request.param == "redis_session_backend_config":
        return pytest.skip("")
    return cast("Union[ServerSideSessionConfig, CookieBackendConfig]", request.getfixturevalue(request.param))


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
def server_side_session_backend(request: pytest.FixtureRequest) -> ServerSideBackend:
    return cast("ServerSideBackend", request.getfixturevalue(request.param))


@pytest.fixture
def session_middleware(session_backend: BaseSessionBackend) -> SessionMiddleware[Any]:
    return SessionMiddleware(app=mock_asgi_app, backend=session_backend)


@pytest.fixture
def cookie_session_middleware(cookie_session_backend: CookieBackend) -> SessionMiddleware[CookieBackend]:
    return SessionMiddleware(app=mock_asgi_app, backend=cookie_session_backend)
