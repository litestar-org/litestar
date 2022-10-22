import os
from typing import Any, TYPE_CHECKING
import secrets
from datetime import timedelta
import pytest

from pydantic import SecretBytes

from starlite.middleware.session import SessionMiddleware
from starlite.middleware.session.cookie_backend import CookieBackend, CookieBackendConfig
from starlite.middleware.session.file_backend import FileBackend, FileBackendConfig
from starlite.middleware.session.memcached_backend import MemcachedBackend, MemcachedBackendConfig
from starlite.middleware.session.memory_backend import MemoryBackend, MemoryBackendConfig
from starlite.middleware.session.redis_backend import RedisBackend, RedisBackendConfig

import fakeredis.aioredis

from starlite.middleware.session.base import BaseBackendConfig, SessionBackend
from tests.fake_memcached import FakeAsyncMemcached


if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


@pytest.fixture
def cookie_backend_config() -> CookieBackendConfig:
    return CookieBackendConfig(secret=SecretBytes(os.urandom(16)))


@pytest.fixture()
def cookie_session_backend(cookie_backend_config) -> CookieBackend:
    return CookieBackend(config=cookie_backend_config)


@pytest.fixture
def memory_backend_config() -> MemoryBackendConfig:
    return MemoryBackendConfig(expires=timedelta(seconds=10))


@pytest.fixture
def file_backend_config(tmp_path) -> FileBackendConfig:
    return FileBackendConfig(storage_path=tmp_path, expires=timedelta(seconds=10))


@pytest.fixture
def redis_backend_config() -> RedisBackendConfig:
    return RedisBackendConfig(redis=fakeredis.aioredis.FakeRedis(), expires=timedelta(seconds=10))


@pytest.fixture
def memcached_backend_config() -> MemcachedBackendConfig:
    return MemcachedBackendConfig(memcached=FakeAsyncMemcached(), expires=10)


@pytest.fixture
def memory_session_backend(memory_backend_config) -> MemoryBackend:
    return MemoryBackend(config=memory_backend_config)


@pytest.fixture
def file_session_backend(file_backend_config) -> MemoryBackend:
    return FileBackend(config=file_backend_config)


@pytest.fixture
def redis_session_backend(redis_backend_config) -> RedisBackend:
    return RedisBackend(config=redis_backend_config)


@pytest.fixture
def memcached_session_backend(memcached_backend_config) -> MemcachedBackend:
    return MemcachedBackend(config=memcached_backend_config)


@pytest.fixture(
    params=[
        pytest.param("cookie_backend_config", id="cookie"),
        pytest.param("memory_backend_config", id="memory"),
        pytest.param("file_backend_config", id="file"),
        pytest.param("redis_backend_config", id="redis"),
        pytest.param("memcached_backend_config", id="memcached"),
    ]
)
def session_backend_config(request) -> BaseBackendConfig:
    return request.getfixturevalue(request.param)


@pytest.fixture(
    params=[
        pytest.param("cookie_session_backend", id="cookie"),
        pytest.param("memory_session_backend", id="memory"),
        pytest.param("file_session_backend", id="file"),
        pytest.param("redis_session_backend", id="redis"),
        pytest.param("memcached_session_backend", id="memcached"),
    ]
)
def session_backend(request) -> SessionBackend:
    return request.getfixturevalue(request.param)


@pytest.fixture
def session_middleware(session_backend) -> SessionMiddleware[Any]:
    return SessionMiddleware(app=mock_asgi_app, backend=session_backend)


@pytest.fixture
def cookie_session_middleware(cookie_session_backend) -> SessionMiddleware[CookieBackend]:
    return SessionMiddleware(app=mock_asgi_app, backend=cookie_session_backend)


@pytest.fixture()
def session_test_cookies(cookie_session_middleware) -> str:
    # Put random data. If you are also handling session management then use session_middleware fixture and create
    # session cookies with your own data.
    _session = {"key": secrets.token_hex(16)}
    return "; ".join(
        f"session-{i}={serialize.decode('utf-8')}"
        for i, serialize in enumerate(cookie_session_middleware.dump_data(_session))
    )
