from __future__ import annotations
from datetime import datetime
import pydantic as pydantic_v2
import pytest
from litestar import post
from litestar.dto import DTOConfig
from litestar.plugins.pydantic import PydanticDTO
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client

def test_pydantic_dto_datetime_validation_issue_4481() -> None:
    class Foo(pydantic_v2.BaseModel):
        date: datetime

    class FooDTO(PydanticDTO[Foo]):
        config = DTOConfig()

    @post("/", dto=FooDTO)
    async def handler(data: Foo) -> None:
        return None

    # This format is valid in Pydantic but invalid in RFC3339 (missing seconds)
    payload = {"date": "2025-05-23T12:20"}

    with create_test_client(handler) as client:
        response = client.post("/", json=payload)
        assert response.status_code == HTTP_201_CREATED
