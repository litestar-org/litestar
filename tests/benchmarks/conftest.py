from __future__ import annotations

from collections.abc import Iterator

import pytest

from litestar.dto import AbstractDTO
from litestar.dto._backend import DTOBackend
from tests.benchmarks.helpers import ASGIRunner


@pytest.fixture(scope="session")
def runner() -> Iterator[ASGIRunner]:
    asgi_runner = ASGIRunner()
    yield asgi_runner
    asgi_runner.close()


@pytest.fixture
def reset_dto_backends() -> Iterator[None]:
    """Clear the class-level DTO backend registry.

    Opt-in (not autouse): the registry is keyed by handler id, and clearing it would break
    module-scoped apps whose handlers use DTOs.
    """
    DTOBackend._seen_model_names = set()
    AbstractDTO._dto_backends = {}
    yield
    DTOBackend._seen_model_names = set()
    AbstractDTO._dto_backends = {}
