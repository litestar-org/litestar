from typing import Any

from pydantic import BaseModel, Field, ValidationError

from litestar import post
from litestar.contrib.pydantic.pydantic_dto_factory import PydanticDTO
from litestar.serialization.msgspec_hooks import decode_json
from litestar.testing import create_test_client


def test_pydantic_validation_error_raises_400() -> None:
    class Model(BaseModel):
        foo: str = Field(max_length=2)

    ModelDTO = PydanticDTO[Model]

    @post(dto=ModelDTO)
    def handler(data: Model) -> Model:
        return data

    model_json = {"foo": "too long"}
    expected_errors: dict[str, Any] = {}
    try:
        Model(**model_json)
    except ValidationError as ex:
        expected_errors = decode_json(ex.json())

    with create_test_client(route_handlers=handler) as client:
        response = client.post("/", json=model_json)

        assert response.status_code == 400
        assert response.json()["extra"] == expected_errors
