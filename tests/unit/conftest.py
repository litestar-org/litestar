from typing import Generator

import pytest

from litestar.dto import AbstractDTO
from litestar.dto._backend import DTOBackend


@pytest.fixture(autouse=True)
def reset_cached_dto_backends() -> Generator[None, None, None]:
    DTOBackend._seen_model_names = set()
    AbstractDTO._dto_backends = {}
    yield
    DTOBackend._seen_model_names = set()
    AbstractDTO._dto_backends = {}
