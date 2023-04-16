from __future__ import annotations

from unittest.mock import AsyncMock

from litestar._kwargs.extractors import create_dto_extractor
from litestar.types.empty import Empty
from litestar.utils.signature import ParsedParameter, ParsedType
from tests.dto import MockDTO, Model


async def test_create_dto_extractor_not_dto_annotated() -> None:
    parsed_parameter = ParsedParameter(
        name="data",
        default=Empty,
        parsed_type=ParsedType.from_annotation(Model),
    )
    extractor = create_dto_extractor(parsed_parameter, MockDTO)
    assert await extractor(AsyncMock()) == Model(a=1, b="2")


async def test_create_dto_extractor_dto_annotated() -> None:
    parsed_parameter = ParsedParameter(
        name="data",
        default=Empty,
        parsed_type=ParsedType.from_annotation(MockDTO),
    )
    extractor = create_dto_extractor(parsed_parameter, MockDTO)
    assert isinstance(await extractor(AsyncMock()), MockDTO)
