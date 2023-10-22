from typing import Dict, List, Optional

import attrs
from attrs import define

from litestar import post
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client
from tests.models import DataclassPet


def test_spec_generation() -> None:
    @attrs.define
    class Person:
        first_name: str
        last_name: str
        id: str
        optional: Optional[str]
        complex: Dict[str, List[Dict[str, str]]]
        pets: Optional[List[DataclassPet]]

    @post("/")
    def handler(data: Person) -> Person:
        return data

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema

        assert schema.to_schema()["components"]["schemas"]["Person"] == {
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
                        {"items": {"$ref": "#/components/schemas/DataclassPet"}, "type": "array"},
                    ]
                },
            },
            "type": "object",
            "required": ["complex", "first_name", "id", "last_name"],
            "title": "Person",
        }


def test_parse_attrs_data_in_signature() -> None:
    @define(slots=True, frozen=True)
    class AttrsUser:
        name: str
        email: str

    @post("/")
    async def attrs_data(data: AttrsUser) -> AttrsUser:
        return data

    with create_test_client([attrs_data]) as client:
        response = client.post("/", json={"name": "foo", "email": "e@example.com"})
        assert response.status_code == HTTP_201_CREATED
        assert response.json().get("name") == "foo"
        assert response.json().get("email") == "e@example.com"
