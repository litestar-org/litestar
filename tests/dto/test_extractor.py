from __future__ import annotations

from typing import Any, FrozenSet, List, Set, Tuple
from unittest.mock import AsyncMock

import pytest

from starlite._signature.models import SignatureField
from starlite.dto.kwarg_extractor import create_dto_extractor
from starlite.dto.stdlib.dataclass import DataclassDTO

from . import Model


async def test_extractor_for_scalar_annotation() -> None:
    dto_type = DataclassDTO[Model]
    dto_type.on_startup(Model)

    class FakeParsedParameter:
        annotation = dto_type
        dto = None

    signature_field = SignatureField(
        children=None,
        default_value=None,
        extra={"parsed_parameter": FakeParsedParameter},
        field_type=Any,
        kwarg_model=None,
        name="data",
    )
    extractor = create_dto_extractor(signature_field)
    data = await extractor(AsyncMock(body=AsyncMock(return_value=b'{"a": 1, "b": "two"}')))
    assert isinstance(data, DataclassDTO)


@pytest.mark.parametrize("generic_collection", [List, FrozenSet, Tuple, Set])
async def test_extractor_for_collection_annotation(generic_collection: Any) -> None:
    dto_type = DataclassDTO[generic_collection[Model]]
    dto_type.on_startup(generic_collection[Model])

    class FakeParsedParameter:
        annotation = dto_type
        dto = None

    signature_field = SignatureField(
        children=None,
        default_value=None,
        extra={"parsed_parameter": FakeParsedParameter},
        field_type=Any,
        kwarg_model=None,
        name="data",
    )
    extractor = create_dto_extractor(signature_field)
    data = await extractor(AsyncMock(body=AsyncMock(return_value=b'[{"a": 1, "b": "two"}]')))
    assert isinstance(data, DataclassDTO)
    for item in data.data:
        assert isinstance(item, Model)
