from __future__ import annotations

import asyncio
import importlib.util
import logging
import random
import string
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
import pytest
from _pytest.fixtures import FixtureRequest
from _pytest.nodes import Item
from fakeredis.aioredis import FakeRedis
from freezegun import freeze_time
from pytest_docker.plugin import Services
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

if TYPE_CHECKING:
    from types import ModuleType

    from freezegun.api import FrozenDateTimeFactory
    from pytest import MonkeyPatch

    from litestar import Litestar
    from litestar.types import (
        AnyIOBackend,
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


async def mock_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
    pass


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
def session_middleware(session_backend: BaseSessionBackend) -> SessionMiddleware[Any]:
    return SessionMiddleware(app=mock_asgi_app, backend=session_backend)


@pytest.fixture
def cookie_session_middleware(
    cookie_session_backend: ClientSideSessionBackend,
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


# Docker services


class DockerServiceRegistry:
    """Registry for docker services. Allows to register fixtures and collect requested
    services for this test session
    """

    def __init__(self) -> None:
        self._fixture_services: dict[str, str] = {}
        self.requested_services: set[str] = set()

    def register(self, service_name: str) -> Callable[[Callable], Callable]:
        """Register a service, making it available via a fixture"""

        def decorator(fn: Callable) -> Callable:
            self._fixture_services[fn.__name__] = service_name
            return pytest.fixture(scope="session")(fn)

        return decorator

    def notify_fixture(self, fixture_name: str) -> None:
        if service_name := self._fixture_services.get(fixture_name):
            self.requested_services.add(service_name)


docker_service_registry = DockerServiceRegistry()


@pytest.fixture(scope="session")
def docker_compose_file() -> Path:
    """
    Returns:
        Path to the docker-compose file for end-to-end test environment.
    """
    return Path(__file__).parent / "docker-compose.yml"


@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    """Need the event loop scoped to the session so that we can use it to check
    containers are ready in session scoped containers fixture."""
    policy = get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_setup() -> str:
    command = "up --build -d"
    for item in docker_service_registry.requested_services:
        command += f" {item}"
    return command


def pytest_collection_modifyitems(items: list[Item]) -> None:
    """Check items if they make use of docker service fixtures and notify the registry"""
    for item in items:
        for marker in item.iter_markers(name="usefixtures"):
            for arg in marker.args:
                docker_service_registry.notify_fixture(arg)


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


@docker_service_registry.register("redis")
async def redis_service(docker_ip: str, docker_services: Services) -> None:  # pylint: disable=unused-argument
    """Starts containers for required services, fixture waits until they are
    responsive before returning.

    Args:
        docker_ip: the test docker IP
        docker_services: the test docker services
    """
    await wait_until_responsive(timeout=30.0, pause=0.1, check=redis_responsive, host=docker_ip)


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


@docker_service_registry.register("mysql")
async def mysql_service(docker_ip: str, docker_services: Services) -> None:  # pylint: disable=unused-argument
    """Starts containers for required services, fixture waits until they are
    responsive before returning.

    Args:
        docker_ip:
        docker_services:
    """
    await wait_until_responsive(timeout=30.0, pause=0.1, check=mysql_responsive, host=docker_ip)


async def postgres_responsive(host: str) -> bool:
    """
    Args:
        host: docker IP address.

    Returns:
        Boolean indicating if we can connect to the database.
    """
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


@docker_service_registry.register("postgres")
async def postgres_service(docker_ip: str, docker_services: Services) -> None:  # pylint: disable=unused-argument
    """Starts containers for required services, fixture waits until they are
    responsive before returning.

    Args:
        docker_ip:
        docker_services:
    """
    await wait_until_responsive(timeout=30.0, pause=0.1, check=postgres_responsive, host=docker_ip)
