from typing import Any

import pytest
from msgspec import Struct

from litestar import post
from litestar.testing import create_test_client
from tests import (
    AttrsPerson,
    MsgSpecStructPerson,
    PydanticDataClassPerson,
    PydanticPerson,
    TypedDictPerson,
    VanillaDataClassPerson,
)


@pytest.mark.parametrize(
    "cls",
    (
        PydanticPerson,
        VanillaDataClassPerson,
        PydanticDataClassPerson,
        TypedDictPerson,
        MsgSpecStructPerson,
        AttrsPerson,
    ),
)
def test_spec_generation(cls: Any) -> None:
    @post("/")
    def handler(data: cls) -> cls:
        return data

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema

        assert schema.to_schema()["components"]["schemas"][cls.__name__] == {
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "id": {"type": "string"},
                "optional": {"oneOf": [{"type": "null"}, {"type": "string"}]},
                "complex": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                },
                "pets": {
                    "oneOf": [
                        {"type": "null"},
                        {"items": {"$ref": "#/components/schemas/PydanticPet"}, "type": "array"},
                    ]
                },
            },
            "type": "object",
            "required": ["complex", "first_name", "id", "last_name"],
            "title": f"{cls.__name__}",
        }


def test_msgspec_schema() -> None:
    class CamelizedStruct(Struct, rename="camel"):
        field_one: int
        field_two: float

    @post("/")
    def handler(data: CamelizedStruct) -> CamelizedStruct:
        return data

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema

        assert schema.to_schema()["components"]["schemas"][CamelizedStruct.__name__] == {
            "properties": {"fieldOne": {"type": "integer"}, "fieldTwo": {"type": "number"}},
            "required": ["fieldOne", "fieldTwo"],
            "title": "CamelizedStruct",
            "type": "object",
        }
