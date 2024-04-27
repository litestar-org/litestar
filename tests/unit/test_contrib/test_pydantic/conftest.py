from __future__ import annotations

import pydantic
import pytest
from pydantic import v1 as pydantic_v1
from pytest import FixtureRequest

from litestar.contrib.pydantic.pydantic_init_plugin import (  # type: ignore[attr-defined]
    _KWARG_META_EXTRACTORS,
    ConstrainedFieldMetaExtractor,
)

from . import PydanticVersion


@pytest.fixture(autouse=True, scope="session")
def ensure_metadata_extractor_is_added() -> None:
    _KWARG_META_EXTRACTORS.add(ConstrainedFieldMetaExtractor)


@pytest.fixture(params=["v1", "v2"])
def pydantic_version(request: FixtureRequest) -> PydanticVersion:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture()
def base_model(pydantic_version: PydanticVersion) -> type[pydantic.BaseModel | pydantic_v1.BaseModel]:
    return pydantic_v1.BaseModel if pydantic_version == "v1" else pydantic.BaseModel
