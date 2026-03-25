from __future__ import annotations

from collections.abc import Callable

import pydantic
import pytest
from pytest import FixtureRequest

from . import PydanticVersion


@pytest.fixture
def int_factory() -> Callable[[], int]:
    return lambda: 2


@pytest.fixture(params=["v2"])
def pydantic_version(request: FixtureRequest) -> PydanticVersion:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture()
def base_model(pydantic_version: PydanticVersion) -> type[pydantic.BaseModel]:
    return pydantic.BaseModel
