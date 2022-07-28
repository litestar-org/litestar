import pathlib
from typing import AsyncGenerator

import pytest

from tests.plugins.tortoise_orm import cleanup, init_tortoise


@pytest.fixture()
def template_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


@pytest.fixture()
async def scaffold_tortoise() -> AsyncGenerator:
    await init_tortoise()
    yield
    await cleanup()


from piccolo.engine.finder import engine_finder


@pytest.mark.asyncio
@pytest.fixture()
async def scaffold_piccolo():
    for table in [
        "ticket",
        "concert",
        "venue",
        "band",
        "manager",
        "poster",
        "migration",
        "musician",
        "recording_studio",
        "shirt",
    ]:
        engine = engine_finder()
        await engine._run_in_new_connection(f"DROP TABLE IF EXISTS {table}")