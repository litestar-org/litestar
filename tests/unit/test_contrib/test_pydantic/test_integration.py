from __future__ import annotations

from typing import Any

from pydantic import VERSION, BaseModel, Field

from litestar import post
from litestar.contrib.pydantic.pydantic_dto_factory import PydanticDTO
from litestar.testing import create_test_client
from tests.models import PydanticPerson


def test_pydantic_validation_error_raises_400() -> None:
    class Model(BaseModel):
        foo: str = Field(max_length=2)

    ModelDTO = PydanticDTO[Model]

    @post(dto=ModelDTO, signature_types=[Model])
    def handler(data: Model) -> Model:
        return data

    model_json = {"foo": "too long"}
    expected_errors: list[dict[str, Any]]

    if VERSION.startswith("1"):
        expected_errors = [
            {
                "loc": ["foo"],
                "msg": "ensure this value has at most 2 characters",
                "type": "value_error.any_str.max_length",
                "ctx": {"limit_value": 2},
            }
        ]
    else:
        expected_errors = [
            {
                "type": "string_too_long",
                "loc": ["foo"],
                "msg": "String should have at most 2 characters",
                "input": "too long",
                "ctx": {"max_length": 2},
            }
        ]

    with create_test_client(route_handlers=handler) as client:
        response = client.post("/", json=model_json)

        assert response.status_code == 400

        extra = response.json()["extra"]

        if VERSION.startswith("2"):
            # the URL keeps on changing as per the installed pydantic version
            extra[0].pop("url")

        assert extra == expected_errors


def test_default_handling_of_pydantic_errors() -> None:
    @post("/{param:int}")
    def my_route_handler(param: int, data: PydanticPerson) -> None:
        ...

    with create_test_client(my_route_handler) as client:
        response = client.post("/123", json={"first_name": "moishe"})
        extra = response.json().get("extra")
        assert extra is not None
        assert 3 if len(extra) == VERSION.startswith("1") else 4
