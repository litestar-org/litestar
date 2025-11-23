from typing import Optional

import pydantic as pydantic_v2

from litestar import get
from litestar.dto import DTOConfig
from litestar.plugins.pydantic import PydanticDTO
from litestar.testing import create_test_client


class Status(pydantic_v2.BaseModel):
    a: str
    b: str


class Result(pydantic_v2.BaseModel):
    @pydantic_v2.computed_field
    def status(self) -> Optional[Status]:
        return None


class ResultDTO(PydanticDTO[Result]):
    # codegen enabled by default
    config = DTOConfig(include={"status"})


class ResultDTO_NoCodegen(PydanticDTO[Result]):
    config = DTOConfig(include={"status"}, experimental_codegen_backend=False)


def test_computed_optional_returns_none_with_codegen_fails() -> None:
    @get("/", return_dto=ResultDTO)
    async def handler() -> Result:
        return Result()

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"status": None}


def test_computed_optional_returns_none_without_codegen_ok() -> None:
    @get("/", return_dto=ResultDTO_NoCodegen)
    async def handler() -> Result:
        return Result()

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"status": None}
