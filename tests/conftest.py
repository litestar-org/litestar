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
