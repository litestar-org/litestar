from typing import Generator

import pytest

from litestar.dto import AbstractDTO


@pytest.fixture(autouse=True)
def reset_cached_dto_backends() -> Generator[None, None, None]:
    AbstractDTO._dto_backends = {}
    yield
    AbstractDTO._dto_backends = {}
