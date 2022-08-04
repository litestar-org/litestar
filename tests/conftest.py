import os
import pathlib
from typing import AsyncGenerator

import pytest
from piccolo.conf.apps import Finder
from piccolo.table import create_db_tables, drop_db_tables

from tests.plugins.tortoise_orm import cleanup, init_tortoise


@pytest.fixture()
def template_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


@pytest.fixture()
async def scaffold_tortoise() -> AsyncGenerator:
    await init_tortoise()
    yield
    await cleanup()


@pytest.fixture()
async def scaffold_piccolo() -> AsyncGenerator:
    os.environ["PICCOLO_CONF"] = "tests.piccolo_conf"
    TABLES = Finder().get_table_classes()
    await drop_db_tables(*TABLES)
    await create_db_tables(*TABLES)
    yield
    await drop_db_tables(*TABLES)
