from __future__ import annotations

from unittest.mock import MagicMock

from starlite._kwargs.extractors import create_dto_extractor
from starlite.types.empty import Empty
from starlite.types.parsed_signature import ParsedParameter, ParsedType
from tests.dto import MockDTO, Model


async def test_create_dto_extractor_not_dto_annotated() -> None:
    parsed_parameter = ParsedParameter(
        name="data",
        default=Empty,
        parsed_type=ParsedType.from_annotation(Model),
    )
    extractor = create_dto_extractor(parsed_parameter, MockDTO)  # type:ignore[type-abstract]
    assert await extractor(MagicMock()) == Model(a=1, b="2")


async def test_create_dto_extractor_dto_annotated() -> None:
    parsed_parameter = ParsedParameter(
        name="data",
        default=Empty,
        parsed_type=ParsedType.from_annotation(MockDTO),
    )
    extractor = create_dto_extractor(parsed_parameter, MockDTO)  # type:ignore[type-abstract]
    assert isinstance(await extractor(MagicMock()), MockDTO)
