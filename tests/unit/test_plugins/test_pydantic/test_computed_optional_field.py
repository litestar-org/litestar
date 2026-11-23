from typing import Optional

import pydantic

from litestar import get
from litestar.dto import DTOConfig
from litestar.plugins.pydantic import PydanticDTO
from litestar.testing import create_test_client


class Status(pydantic.BaseModel):
    a: str
    b: str


class Result(pydantic.BaseModel):
    @pydantic.computed_field
    def status(self) -> Optional[Status]:
        return None


class ResultDTO(PydanticDTO[Result]):
    config = DTOConfig(include={"status"})


def test_computed_optional_returns_none() -> None:
    @get("/", return_dto=ResultDTO)
    async def handler() -> Result:
        return Result()

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"status": None}
