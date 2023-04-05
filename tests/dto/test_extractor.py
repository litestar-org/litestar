from __future__ import annotations

from typing import Any, FrozenSet, List, Set, Tuple
from unittest.mock import AsyncMock

import pytest

from starlite import post
from starlite.dto.factory.stdlib.dataclass import DataclassDTO
from starlite.dto.kwarg_extractor import create_dto_extractor
from starlite.types.empty import Empty
from starlite.types.parsed_signature import ParsedParameter, ParsedType

from . import Model


async def test_extractor_for_scalar_annotation() -> None:
    dto_type = DataclassDTO[Model]
    dto_type.on_startup(Model, post())

    parsed_param = ParsedParameter(
        name="data",
        default=Empty,
        parsed_type=ParsedType.from_annotation(dto_type),
    )
    extractor = create_dto_extractor(parsed_param, dto_type)
    data = await extractor(
        AsyncMock(body=AsyncMock(return_value=b'{"a": 1, "b": "two"}'), content_type=("application/json",))
    )
    assert isinstance(data, DataclassDTO)


@pytest.mark.parametrize("generic_collection", [List, FrozenSet, Tuple, Set])
async def test_extractor_for_collection_annotation(generic_collection: Any) -> None:
    dto_type = DataclassDTO[generic_collection[Model]]
    dto_type.on_startup(generic_collection[Model], post())

    parsed_param = ParsedParameter(
        name="data",
        default=Empty,
        parsed_type=ParsedType.from_annotation(dto_type),
    )

    extractor = create_dto_extractor(parsed_param, dto_type)
    data = await extractor(
        AsyncMock(body=AsyncMock(return_value=b'[{"a": 1, "b": "two"}]'), content_type=("application/json",))
    )
    assert isinstance(data, DataclassDTO)
    for item in data.data:
        assert isinstance(item, Model)
