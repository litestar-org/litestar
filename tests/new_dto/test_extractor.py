from __future__ import annotations

from typing import Any, FrozenSet, List, Set, Tuple
from unittest.mock import AsyncMock

import pytest

from starlite._signature.models import SignatureField
from starlite.new_dto.kwarg_extractor import create_dto_extractor

from . import ConcreteDTO


async def test_extractor_for_scalar_annotation() -> None:
    signature_field = SignatureField(
        children=None, default_value=None, extra={}, field_type=ConcreteDTO, kwarg_model=None, name="data"
    )
    extractor = create_dto_extractor(signature_field)
    data = await extractor(AsyncMock(body=AsyncMock(return_value=b"")))
    assert isinstance(data, ConcreteDTO)


@pytest.mark.parametrize(
    "field_type",
    [
        List[ConcreteDTO],
        FrozenSet[ConcreteDTO],
        Tuple[ConcreteDTO, ...],
        Tuple[ConcreteDTO, ConcreteDTO],
        Set[ConcreteDTO],
    ],
)
async def test_extractor_for_collection_annotation(field_type: Any) -> None:
    signature_field = SignatureField(
        children=None, default_value=None, extra={}, field_type=field_type, kwarg_model=None, name="data"
    )
    extractor = create_dto_extractor(signature_field)
    data = await extractor(AsyncMock(body=AsyncMock(return_value=b"")))
    assert isinstance(data, list)
    for item in data:
        assert isinstance(item, ConcreteDTO)
