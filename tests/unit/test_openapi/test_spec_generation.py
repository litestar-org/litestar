import json
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest
from msgspec import Struct

from litestar import delete, post
from litestar.openapi import ResponseSpec
from litestar.openapi.spec import OpenAPI
from litestar.params import JSONBody
from litestar.status_codes import HTTP_204_NO_CONTENT
from litestar.testing import create_test_client
from tests.models import DataclassPerson, MsgSpecStructPerson, TypedDictPerson

NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}
LIBRARY_REQUIRED = ["first_name", "last_name", "id", "optional", "complex"]


@pytest.mark.parametrize(
    ("cls", "union", "optional", "required"),
    [
        pytest.param(DataclassPerson, "anyOf", NULLABLE_STRING, LIBRARY_REQUIRED, id="dataclass"),
        pytest.param(
            TypedDictPerson,
            "oneOf",
            {"type": ["string", "null"]},
            ["complex", "first_name", "id", "last_name"],
            id="typed-dict",
        ),
        pytest.param(MsgSpecStructPerson, "anyOf", NULLABLE_STRING, [*LIBRARY_REQUIRED, "pets"], id="struct"),
    ],
)
def test_spec_generation(cls: Any, union: str, optional: dict[str, Any], required: list[str]) -> None:
    @post("/")
    def handler(data: JSONBody[cls]) -> cls:  # pyright: ignore[reportInvalidTypeForm]
        return data

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema
        assert schema.to_schema()["components"]["schemas"][cls.__name__] == {
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "id": {"type": "string"},
                "optional": optional,
                "complex": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                },
                "pets": {
                    union: [
                        {
                            "items": {"$ref": "#/components/schemas/DataclassPet"},
                            "type": "array",
                        },
                        {"type": "null"},
                    ]
                },
            },
            "type": "object",
            "required": required,
            "title": f"{cls.__name__}",
        }


def test_spec_generation_no_content() -> None:
    @delete(
        "/",
        status_code=HTTP_204_NO_CONTENT,
        responses={204: ResponseSpec(None, description="Custom response")},
    )
    def handler() -> None:
        return None

    with create_test_client(handler) as client:
        schema: OpenAPI = client.app.openapi_schema
        assert schema.to_schema()["paths"] == {
            "/": {
                "delete": {
                    "summary": "Handler",
                    "deprecated": False,
                    "operationId": "Handler",
                    "responses": {
                        "204": {
                            "description": "Custom response",
                        }
                    },
                },
            },
        }


def test_msgspec_schema() -> None:
    class CamelizedStruct(Struct, rename="camel"):
        field_one: int
        field_two: float

    @post("/")
    def handler(data: JSONBody[CamelizedStruct]) -> CamelizedStruct:
        return data

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema

        assert schema.to_schema()["components"]["schemas"]["CamelizedStruct"] == {
            "properties": {"fieldOne": {"type": "integer"}, "fieldTwo": {"type": "number"}},
            "required": ["fieldOne", "fieldTwo"],
            "title": "CamelizedStruct",
            "type": "object",
        }


MODULE_CONTENT = """
from __future__ import annotations

from msgspec import Struct

from litestar import Litestar, get

class A(Struct):
    a: A
    b: B
    opt_a: A | None = None
    opt_b: B | None = None
    list_a: list[A] = []
    list_b: list[B] = []

class B(Struct):
    a: A
    b: B
    opt_a: A | None = None
    opt_b: B | None = None
    list_a: list[A] = []
    list_b: list[B] = []

@get("/")
async def test() -> A:
    return A()
"""


def unordered_any_of(node: Any) -> Any:
    if isinstance(node, list):
        return [unordered_any_of(item) for item in node]
    if not isinstance(node, dict):
        return node
    return {
        key: sorted(unordered_any_of(value), key=json.dumps) if key == "anyOf" else unordered_any_of(value)
        for key, value in node.items()
    }


def test_recursive_schema_generation(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(MODULE_CONTENT)
    with create_test_client(module.test, debug=True) as client:
        schema = client.app.openapi_schema
        assert schema
        assert unordered_any_of(schema.to_schema()["components"]["schemas"]["A"]) == unordered_any_of(
            {
                "required": ["a", "b"],
                "properties": {
                    "a": {"$ref": "#/components/schemas/A"},
                    "b": {"$ref": "#/components/schemas/B"},
                    "opt_a": {"anyOf": [{"type": "null"}, {"$ref": "#/components/schemas/A"}]},
                    "opt_b": {"anyOf": [{"type": "null"}, {"$ref": "#/components/schemas/B"}]},
                    "list_a": {"items": {"$ref": "#/components/schemas/A"}, "type": "array", "default": []},
                    "list_b": {"items": {"$ref": "#/components/schemas/B"}, "type": "array", "default": []},
                },
                "type": "object",
                "title": "A",
            }
        )
        assert unordered_any_of(schema.to_schema()["components"]["schemas"]["B"]) == unordered_any_of(
            {
                "required": ["a", "b"],
                "properties": {
                    "a": {"$ref": "#/components/schemas/A"},
                    "b": {"$ref": "#/components/schemas/B"},
                    "opt_a": {"anyOf": [{"type": "null"}, {"$ref": "#/components/schemas/A"}]},
                    "opt_b": {"anyOf": [{"type": "null"}, {"$ref": "#/components/schemas/B"}]},
                    "list_a": {"items": {"$ref": "#/components/schemas/A"}, "type": "array", "default": []},
                    "list_b": {"items": {"$ref": "#/components/schemas/B"}, "type": "array", "default": []},
                },
                "type": "object",
                "title": "B",
            }
        )
