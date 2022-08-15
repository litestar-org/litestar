import os
import pathlib
from typing import AsyncGenerator, Callable

import pytest
from piccolo.conf.apps import Finder
from piccolo.table import create_db_tables, drop_db_tables

from tests.plugins.tortoise_orm import cleanup, init_tortoise


def pytest_generate_tests(metafunc: Callable) -> None:
    """Sets ENV variables for testing."""
    os.environ.update(PICCOLO_CONF="tests.piccolo_conf")


@pytest.fixture()
def template_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


@pytest.fixture()
async def scaffold_tortoise() -> AsyncGenerator:
    """Scaffolds Tortoise ORM and performs cleanup."""
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
