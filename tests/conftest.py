from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import random
import re
import string
import subprocess
import sys
import timeit
from asyncio import AbstractEventLoop, get_event_loop_policy
from os import urandom
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generator,
    Iterator,
    TypeVar,
    Union,
    cast,
)

import asyncmy
import asyncpg
import oracledb
import pytest
from _pytest.fixtures import FixtureRequest
from fakeredis.aioredis import FakeRedis
from freezegun import freeze_time
from google.auth.credentials import AnonymousCredentials  # pyright: ignore
from google.cloud import spanner  # pyright: ignore
from oracledb.exceptions import DatabaseError, OperationalError
from pytest_lazyfixture import lazy_fixture
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError as RedisConnectionError

from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.base import BaseSessionBackend
from litestar.middleware.session.client_side import (
    ClientSideSessionBackend,
    CookieBackendConfig,
)
from litestar.middleware.session.server_side import (
    ServerSideSessionBackend,
    ServerSideSessionConfig,
)
from litestar.stores.base import Store
from litestar.stores.file import FileStore
from litestar.stores.memory import MemoryStore
from litestar.stores.redis import RedisStore
from litestar.testing import RequestFactory
from litestar.utils.sync import AsyncCallable

if TYPE_CHECKING:
    from types import ModuleType

    from freezegun.api import FrozenDateTimeFactory
    from pytest import MonkeyPatch

    from litestar import Litestar
    from litestar.types import (
        AnyIOBackend,
        ASGIApp,
        ASGIVersion,
        Receive,
        RouteHandlerType,
        Scope,
        ScopeSession,
        Send,
    )


@pytest.fixture()
def template_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture(
    params=[
        pytest.param("asyncio", id="asyncio"),
        pytest.param("trio", id="trio"),
    ]
)
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture()
def mock_asgi_app() -> ASGIApp:
    async def asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
        ...

    return asgi_app


@pytest.fixture()
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture()
def redis_store(fake_redis: FakeRedis) -> RedisStore:
    return RedisStore(redis=fake_redis)


@pytest.fixture()
def memory_store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture()
def file_store(tmp_path: Path) -> FileStore:
    return FileStore(path=tmp_path)


@pytest.fixture(params=["redis_store", "memory_store", "file_store"])
def store(request: FixtureRequest) -> Store:
    return cast("Store", request.getfixturevalue(request.param))


@pytest.fixture
def cookie_session_backend_config() -> CookieBackendConfig:
    return CookieBackendConfig(secret=urandom(16))


@pytest.fixture()
def cookie_session_backend(cookie_session_backend_config: CookieBackendConfig) -> ClientSideSessionBackend:
    return ClientSideSessionBackend(config=cookie_session_backend_config)


@pytest.fixture(
    params=[
        pytest.param(lazy_fixture("cookie_session_backend_config"), id="cookie"),
        pytest.param(lazy_fixture("server_side_session_config"), id="server-side"),
    ]
)
def session_backend_config(request: pytest.FixtureRequest) -> ServerSideSessionConfig | CookieBackendConfig:
    return cast("Union[ServerSideSessionConfig, CookieBackendConfig]", request.param)


@pytest.fixture()
def server_side_session_config() -> ServerSideSessionConfig:
    return ServerSideSessionConfig()


@pytest.fixture()
def server_side_session_backend(server_side_session_config: ServerSideSessionConfig) -> ServerSideSessionBackend:
    return ServerSideSessionBackend(config=server_side_session_config)


@pytest.fixture(
    params=[
        pytest.param("cookie_session_backend", id="cookie"),
        pytest.param("server_side_session_backend", id="server-side"),
    ]
)
def session_backend(request: pytest.FixtureRequest) -> BaseSessionBackend:
    return cast("BaseSessionBackend", request.getfixturevalue(request.param))


@pytest.fixture()
def session_backend_config_memory(memory_store: MemoryStore) -> ServerSideSessionConfig:
    return ServerSideSessionConfig()


@pytest.fixture
def session_middleware(session_backend: BaseSessionBackend, mock_asgi_app: ASGIApp) -> SessionMiddleware[Any]:
    return SessionMiddleware(app=mock_asgi_app, backend=session_backend)


@pytest.fixture
def cookie_session_middleware(
    cookie_session_backend: ClientSideSessionBackend, mock_asgi_app: ASGIApp
) -> SessionMiddleware[ClientSideSessionBackend]:
    return SessionMiddleware(app=mock_asgi_app, backend=cookie_session_backend)


@pytest.fixture
def test_client_backend(anyio_backend_name: str) -> AnyIOBackend:
    return cast("AnyIOBackend", anyio_backend_name)


@pytest.fixture
def create_scope() -> Callable[..., Scope]:
    def inner(
        *,
        type: str = "http",
        app: Litestar | None = None,
        asgi: ASGIVersion | None = None,
        auth: Any = None,
        client: tuple[str, int] | None = ("testclient", 50000),
        extensions: dict[str, dict[object, object]] | None = None,
        http_version: str = "1.1",
        path: str = "/",
        path_params: dict[str, str] | None = None,
        query_string: str = "",
        root_path: str = "",
        route_handler: RouteHandlerType | None = None,
        scheme: str = "http",
        server: tuple[str, int | None] | None = ("testserver", 80),
        session: ScopeSession = None,
        state: dict[str, Any] | None = None,
        user: Any = None,
        **kwargs: dict[str, Any],
    ) -> Scope:
        scope = {
            "app": app,
            "asgi": asgi or {"spec_version": "2.0", "version": "3.0"},
            "auth": auth,
            "type": type,
            "path": path,
            "raw_path": path.encode(),
            "root_path": root_path,
            "scheme": scheme,
            "query_string": query_string.encode(),
            "client": client,
            "server": server,
            "method": "GET",
            "http_version": http_version,
            "extensions": extensions or {"http.response.template": {}},
            "state": state or {},
            "path_params": path_params or {},
            "route_handler": route_handler,
            "user": user,
            "session": session,
            **kwargs,
        }
        return cast("Scope", scope)

    return inner


@pytest.fixture
def scope(create_scope: Callable[..., Scope]) -> Scope:
    return create_scope()


@pytest.fixture
def create_module(tmp_path: Path, monkeypatch: MonkeyPatch) -> Callable[[str], ModuleType]:
    """Utility fixture for dynamic module creation."""

    def wrapped(source: str) -> ModuleType:
        """

        Args:
            source: Source code as a string.

        Returns:
            An imported module.
        """
        T = TypeVar("T")

        def not_none(val: T | T | None) -> T:
            assert val is not None
            return val

        def module_name_generator() -> str:
            letters = string.ascii_lowercase
            return "".join(random.choice(letters) for _ in range(10))

        module_name = module_name_generator()
        path = tmp_path / f"{module_name}.py"
        path.write_text(source)
        # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
        spec = not_none(importlib.util.spec_from_file_location(module_name, path))
        module = not_none(importlib.util.module_from_spec(spec))
        monkeypatch.setitem(sys.modules, module_name, module)
        not_none(spec.loader).exec_module(module)
        return module

    return wrapped


@pytest.fixture(scope="module")
def mock_db() -> MemoryStore:
    return MemoryStore()


@pytest.fixture()
def frozen_datetime() -> Generator[FrozenDateTimeFactory, None, None]:
    with freeze_time() as frozen:
        yield cast("FrozenDateTimeFactory", frozen)


@pytest.fixture()
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture()
def reset_httpx_logging() -> Generator[None, None, None]:
    # ensure that httpx logging is not interfering with our test client
    httpx_logger = logging.getLogger("httpx")
    initial_level = httpx_logger.level
    httpx_logger.setLevel(logging.WARNING)
    yield
    httpx_logger.setLevel(initial_level)


# the monkeypatch fixture does not work with session scoped dependencies
@pytest.fixture(autouse=True, scope="session")
def disable_warn_implicit_sync_to_thread() -> Generator[None, None, None]:
    old_value = os.getenv("LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD")
    os.environ["LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD"] = "0"
    yield
    if old_value is not None:
        os.environ["LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD"] = old_value


@pytest.fixture()
def disable_warn_sync_to_thread_with_async(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_WARN_SYNC_TO_THREAD_WITH_ASYNC", "0")


@pytest.fixture()
def enable_warn_implicit_sync_to_thread(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD", "1")


# Docker services


@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    """Need the event loop scoped to the session so that we can use it to check
    containers are ready in session scoped containers fixture."""
    policy = get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


class DockerServiceRegistry:
    def __init__(self) -> None:
        self._running_services: set[str] = set()
        self.docker_ip = self._get_docker_ip()
        self._base_command = [
            "docker-compose",
            "--file=tests/docker-compose.yml",
            "--project-name=litestar_pytest",
        ]

    def _get_docker_ip(self) -> str:
        docker_host = os.environ.get("DOCKER_HOST", "").strip()
        if not docker_host or docker_host.startswith("unix://"):
            return "127.0.0.1"

        match = re.match(r"^tcp://(.+?):\d+$", docker_host)
        if not match:
            raise ValueError(f'Invalid value for DOCKER_HOST: "{docker_host}".')
        return match.group(1)

    def run_command(self, *args: str) -> None:
        subprocess.run([*self._base_command, *args], check=True, capture_output=True)

    async def start(
        self,
        name: str,
        *,
        check: Callable[..., Awaitable],
        timeout: float = 30,
        pause: float = 0.1,
        **kwargs: Any,
    ) -> None:
        if name not in self._running_services:
            self.run_command("up", "-d", name)
            self._running_services.add(name)

        await wait_until_responsive(
            check=check,
            timeout=timeout,
            pause=pause,
            host=self.docker_ip,
            **kwargs,
        )

    def stop(self, name: str) -> None:
        pass

    def down(self) -> None:
        self.run_command("down", "-t", "5")


@pytest.fixture(scope="session")
def docker_services() -> Generator[DockerServiceRegistry, None, None]:
    registry = DockerServiceRegistry()
    yield registry
    registry.down()


@pytest.fixture(scope="session")
def docker_ip(docker_services: DockerServiceRegistry) -> str:
    return docker_services.docker_ip


async def wait_until_responsive(
    check: Callable[..., Awaitable],
    timeout: float,
    pause: float,
    **kwargs: Any,
) -> None:
    """Wait until a service is responsive.

    Args:
        check: Coroutine, return truthy value when waiting should stop.
        timeout: Maximum seconds to wait.
        pause: Seconds to wait between calls to `check`.
        **kwargs: Given as kwargs to `check`.
    """
    ref = timeit.default_timer()
    now = ref
    while (now - ref) < timeout:
        if await check(**kwargs):
            return
        await asyncio.sleep(pause)
        now = timeit.default_timer()

    raise Exception("Timeout reached while waiting on service!")


async def redis_responsive(host: str) -> bool:
    """Args:
        host: docker IP address.

    Returns:
        Boolean indicating if we can connect to the redis server.
    """
    client: AsyncRedis = AsyncRedis(host=host, port=6397)
    try:
        return await client.ping()
    except (ConnectionError, RedisConnectionError):
        return False
    finally:
        await client.close()


@pytest.fixture(scope="session")
async def redis_service(docker_services: DockerServiceRegistry) -> None:  # pylint: disable=unused-argument
    await docker_services.start("redis", check=redis_responsive)


async def mysql_responsive(host: str) -> bool:
    """
    Args:
        host: docker IP address.

    Returns:
        Boolean indicating if we can connect to the database.
    """

    try:
        conn = await asyncmy.connect(
            host=host,
            port=3360,
            user="app",
            database="db",
            password="super-secret",
        )
        async with conn.cursor() as cursor:
            await cursor.execute("select 1 as is_available")
            resp = await cursor.fetchone()
        return bool(resp[0] == 1)
    except asyncmy.errors.OperationalError:  # pyright: ignore
        return False


@pytest.fixture(scope="session")
async def mysql_service(docker_services: DockerServiceRegistry) -> None:
    await docker_services.start("mysql", check=mysql_responsive)


async def postgres_responsive(host: str) -> bool:
    try:
        conn = await asyncpg.connect(
            host=host, port=5423, user="postgres", database="postgres", password="super-secret"
        )
    except (ConnectionError, asyncpg.CannotConnectNowError):
        return False

    try:
        return (await conn.fetchrow("SELECT 1"))[0] == 1  # type: ignore
    finally:
        await conn.close()


@pytest.fixture(scope="session")
async def postgres_service(docker_services: DockerServiceRegistry) -> None:
    await docker_services.start("postgres", check=postgres_responsive)


def oracle_responsive(host: str) -> bool:
    try:
        conn = oracledb.connect(
            host=host,
            port=1512,
            user="app",
            service_name="xepdb1",
            password="super-secret",
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM dual")
            resp = cursor.fetchone()
        return bool(resp[0] == 1)
    except (OperationalError, DatabaseError):  # pyright: ignore
        return False


@pytest.fixture(scope="session")
async def oracle_service(docker_services: DockerServiceRegistry) -> None:
    await docker_services.start("oracle", check=AsyncCallable(oracle_responsive), timeout=60)


def spanner_responsive(host: str) -> bool:
    try:
        os.environ["SPANNER_EMULATOR_HOST"] = "localhost:9010"
        os.environ["GOOGLE_CLOUD_PROJECT"] = "emulator-test-project"
        spanner_client = spanner.Client(project="emulator-test-project", credentials=AnonymousCredentials())
        instance = spanner_client.instance("test-instance")
        try:
            instance.create()
        except Exception:  # pyright: ignore
            pass
        database = instance.database("test-database")
        try:
            database.create()
        except Exception:  # pyright: ignore
            pass
        with database.snapshot() as snapshot:
            resp = list(snapshot.execute_sql("SELECT 1"))[0]
        return bool(resp[0] == 1)
    except Exception:  # pyright: ignore
        return False


@pytest.fixture(scope="session")
async def spanner_service(docker_services: DockerServiceRegistry) -> None:
    os.environ["SPANNER_EMULATOR_HOST"] = "localhost:9010"
    await docker_services.start("spanner", timeout=60, check=AsyncCallable(spanner_responsive))
