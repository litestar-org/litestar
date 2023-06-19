from __future__ import annotations

from unittest.mock import AsyncMock

from litestar._kwargs.extractors import create_dto_extractor
from tests.test_dto import MockDTO, Model


async def test_create_dto_extractor() -> None:
    extractor = create_dto_extractor(MockDTO)
    assert await extractor(AsyncMock()) == Model(a=1, b="2")
