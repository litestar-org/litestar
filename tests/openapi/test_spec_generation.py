from typing import Any

import pytest

from litestar import post
from litestar.testing import create_test_client
from tests import (
    AttrsPerson,
    MsgSpecStructPerson,
    Person,
    PydanticDataClassPerson,
    TypedDictPerson,
    VanillaDataClassPerson,
)


@pytest.mark.parametrize(
    "cls", (Person, VanillaDataClassPerson, PydanticDataClassPerson, TypedDictPerson, MsgSpecStructPerson, AttrsPerson)
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
                "complex": {"type": "object"},
                "pets": {
                    "oneOf": [
                        {"type": "null"},
                        {"items": {"$ref": "#/components/schemas/Pet"}, "type": "array"},
                    ]
                },
            },
            "type": "object",
            "required": ["complex", "first_name", "id", "last_name"],
            "title": f"{cls.__name__}",
        }
