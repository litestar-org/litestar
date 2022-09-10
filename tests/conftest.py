import os
import pathlib
import secrets
from typing import TYPE_CHECKING, AsyncGenerator, Callable

import pytest
from piccolo.conf.apps import Finder
from piccolo.table import create_db_tables, drop_db_tables
from pydantic import SecretBytes

from starlite.middleware.session import SessionCookieConfig, SessionMiddleware

if TYPE_CHECKING:
    from starlette.types import Receive, Scope, Send


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


#############################
# Session Middleware Fixtures
#############################
async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


@pytest.fixture()
def session_middleware() -> SessionMiddleware:
    return SessionMiddleware(app=mock_asgi_app, config=SessionCookieConfig(secret=SecretBytes(os.urandom(16))))


@pytest.fixture()
def session_test_cookies(session_middleware: SessionMiddleware) -> str:
    # Put random data. If you are also handling session management then use session_middleware fixture and create
    # session cookies with your own data.
    _session = {"key": secrets.token_hex(16)}
    cookies = ";".join(
        f"session-{i}={serialize.decode('utf-8')}" for i, serialize in enumerate(session_middleware.dump_data(_session))
    )
    return cookies
