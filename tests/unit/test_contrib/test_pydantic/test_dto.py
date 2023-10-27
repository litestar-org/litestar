from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Request, post
from litestar.contrib.pydantic import PydanticDTO, _model_dump_json
from litestar.dto import DTOConfig
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from pydantic import BaseModel


def test_schema_required_fields_with_pydantic_dto(
    use_experimental_dto_backend: bool, base_model: type[BaseModel]
) -> None:
    class PydanticUser(base_model):  # type: ignore[misc, valid-type]
        age: int
        name: str

    class UserDTO(PydanticDTO[PydanticUser]):
        config = DTOConfig(experimental_codegen_backend=use_experimental_dto_backend)

    @post(dto=UserDTO, return_dto=None, signature_types=[PydanticUser])
    def handler(data: PydanticUser, request: Request) -> dict:
        schema = request.app.openapi_schema
        return schema.to_schema()

    with create_test_client(handler) as client:
        data = PydanticUser(name="A", age=10)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        received = client.post(
            "/",
            content=_model_dump_json(data),
            headers=headers,
        )
        required = next(iter(received.json()["components"]["schemas"].values()))["required"]
        assert len(required) == 2
