import importlib.util
import sys
from os import environ, urandom
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Optional,
    Tuple,
    TypeVar,
    Union,
)
from uuid import uuid4

from piccolo.conf.apps import Finder
from piccolo.table import create_db_tables, drop_db_tables
from pytest_lazyfixture import lazy_fixture

from starlite.middleware.session import SessionMiddleware
from starlite.middleware.session.base import BaseSessionBackend
from starlite.middleware.session.client_side import (
    ClientSideSessionBackend,
    CookieBackendConfig,
)
from starlite.middleware.session.server_side import (
    ServerSideSessionBackend,
    ServerSideSessionConfig,
)
from starlite.storage.base import Storage

if TYPE_CHECKING:
    from types import ModuleType

    from pytest import MonkeyPatch

    from starlite import Starlite
    from starlite.types import (
        AnyIOBackend,
        ASGIVersion,
        Receive,
        RouteHandlerType,
        Scope,
        ScopeSession,
        Send,
    )

from pathlib import Path
from typing import cast

import pytest
from _pytest.fixtures import FixtureRequest
from fakeredis.aioredis import FakeRedis

from starlite.storage.file import FileStorage
from starlite.storage.memory import MemoryStorage
from starlite.storage.redis import RedisStorage


def pytest_generate_tests(metafunc: Callable) -> None:
    """Sets ENV variables for 9-testing."""
    environ.update(PICCOLO_CONF="tests.piccolo_conf")


@pytest.fixture()
def template_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
async def scaffold_tortoise() -> AsyncGenerator:
    """Scaffolds Tortoise ORM and performs cleanup."""
    from tests.contrib.tortoise_orm import cleanup, init_tortoise

    await init_tortoise()
    yield
    await cleanup()


@pytest.fixture()
async def scaffold_piccolo() -> AsyncGenerator:
    """Scaffolds Piccolo ORM and performs cleanup."""
    tables = Finder().get_table_classes()
    await drop_db_tables(*tables)
    await create_db_tables(*tables)
    yield
    await drop_db_tables(*tables)


@pytest.fixture(
    params=[
        pytest.param("asyncio", id="asyncio"),
        pytest.param("trio", id="trio"),
    ]
)
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return request.param  # type: ignore[no-any-return]


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


@pytest.fixture()
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture()
def redis_storage_backend(fake_redis: FakeRedis) -> RedisStorage:
    return RedisStorage(redis=fake_redis)


@pytest.fixture()
def memory_storage_backend() -> MemoryStorage:
    return MemoryStorage()


@pytest.fixture()
def file_storage_backend(tmp_path: Path) -> FileStorage:
    return FileStorage(path=tmp_path)


@pytest.fixture(
    params=[
        "redis_storage_backend",
        "memory_storage_backend",
        "file_storage_backend",
    ]
)
def storage_backend(request: FixtureRequest) -> Storage:
    return cast("Storage", request.getfixturevalue(request.param))


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
def session_backend_config(request: pytest.FixtureRequest) -> Union[ServerSideSessionConfig, CookieBackendConfig]:
    return cast("Union[ServerSideSessionConfig, CookieBackendConfig]", request.param)


@pytest.fixture()
def server_side_session_config(storage_backend: Storage) -> ServerSideSessionConfig:
    return ServerSideSessionConfig(storage=storage_backend)


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
def session_backend_config_memory(memory_storage_backend: MemoryStorage) -> ServerSideSessionConfig:
    return ServerSideSessionConfig(storage=memory_storage_backend)


@pytest.fixture
def session_middleware(session_backend: BaseSessionBackend) -> SessionMiddleware[Any]:
    return SessionMiddleware(app=mock_asgi_app, backend=session_backend)


@pytest.fixture
def cookie_session_middleware(
    cookie_session_backend: ClientSideSessionBackend,
) -> SessionMiddleware[ClientSideSessionBackend]:
    return SessionMiddleware(app=mock_asgi_app, backend=cookie_session_backend)


@pytest.fixture
def test_client_backend(anyio_backend_name: str) -> "AnyIOBackend":
    return cast("AnyIOBackend", anyio_backend_name)


@pytest.fixture
def create_scope() -> Callable[..., "Scope"]:
    def inner(
        *,
        type: str = "http",
        app: Optional["Starlite"] = None,
        asgi: Optional["ASGIVersion"] = None,
        auth: Any = None,
        client: Optional[Tuple[str, int]] = ("testclient", 50000),
        extensions: Optional[Dict[str, Dict[object, object]]] = None,
        http_version: str = "1.1",
        path: str = "/",
        path_params: Optional[Dict[str, str]] = None,
        query_string: str = "",
        root_path: str = "",
        route_handler: Optional["RouteHandlerType"] = None,
        scheme: str = "http",
        server: Optional[Tuple[str, Optional[int]]] = ("testserver", 80),
        session: "ScopeSession" = None,
        state: Optional[Dict[str, Any]] = None,
        user: Any = None,
        **kwargs: Dict[str, Any],
    ) -> "Scope":
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
def scope(create_scope: Callable[..., "Scope"]) -> "Scope":
    return create_scope()


@pytest.fixture
def create_module(tmp_path: Path, monkeypatch: "MonkeyPatch") -> "Callable[[str], ModuleType]":
    """Utility fixture for dynamic module creation."""

    def wrapped(source: str) -> "ModuleType":
        """

        Args:
            source: Source code as a string.

        Returns:
            An imported module.
        """
        T = TypeVar("T")

        def not_none(val: Union[T, Optional[T]]) -> T:
            assert val is not None
            return val

        module_name = uuid4().hex
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
def mock_db() -> MemoryStorage:
    return MemoryStorage()
