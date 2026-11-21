from typing import Any

import pytest
from docs.examples.openapi import (
    customize_msgspec_model_schema,
    customize_openapi_types,
    customize_pydantic_model_name,
    customize_pydantic_model_schema,
)

from litestar.testing import TestClient


def test_schema_generation() -> None:
    with TestClient(app=customize_pydantic_model_name.app) as client:
        assert client.app.openapi_schema.to_schema() == {
            "info": {"title": "Litestar API", "version": "1.0.0"},
            "openapi": "3.1.0",
            "servers": [{"url": "/"}],
            "paths": {
                "/id": {
                    "get": {
                        "summary": "RetrieveIdHandler",
                        "operationId": "IdRetrieveIdHandler",
                        "responses": {
                            "200": {
                                "description": "Request fulfilled, document follows",
                                "headers": {},
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/components/schemas/IdContainer"}}
                                },
                            }
                        },
                        "deprecated": False,
                    }
                }
            },
            "components": {
                "schemas": {
                    "IdContainer": {
                        "properties": {"id": {"format": "uuid", "title": "Id", "type": "string"}},
                        "type": "object",
                        "required": ["id"],
                        "title": "IdContainer",
                    }
                }
            },
        }


def test_customize_path() -> None:
    from docs.examples.openapi.customize_path import app

    with TestClient(app=app) as client:
        resp = client.get("/docs/openapi.json")
        assert resp.status_code == 200


def test_schema_types_sorted() -> None:
    """
    Handles an edge case where types are not `oneOf`; instead a bare list of types considered as an enum.

    The following is what the OpenAPI 3.0 spec provides as a consistent way of describing types.
    These types appear to be sorted consistently for other models.

    `{'oneOf': [{'type': 'string', 'const': '1'}, {'type': 'null'}]}`

    The following is what a `Literal | None` type is converted to in the spec. The type field is not sorted
    deterministically, which can result in CI failures due to changed spec generation.

    `{'type': ['null', 'string'], 'enum': ['1', None]}`

    Without this change, the 'type' key above may display `['string', 'null']` depending on the system.
    """
    with TestClient(app=customize_openapi_types.app) as client:
        schema = client.app.openapi_schema.to_schema()

        nested_query_type = schema["paths"]["/"]["post"]["parameters"][0]["schema"]["type"]

        # Types should be sorted alphabetically.
        assert nested_query_type == ["null", "string"]


PRODUCT_PROPERTIES: dict[str, Any] = {
    "name": {"type": "string", "maxLength": 50, "title": "Name", "description": "Display name"},
    "sku": {"type": "string", "pattern": "^[A-Z]{3}-[0-9]{4}$", "title": "Sku"},
    "price": {"type": "integer", "exclusiveMinimum": 0, "title": "Price", "description": "Price in cents"},
}


@pytest.mark.parametrize(
    ("component", "properties", "required"),
    [
        ("Product-Input", PRODUCT_PROPERTIES, ["name", "sku", "price"]),
        (
            "Product-Output",
            {**PRODUCT_PROPERTIES, "label": {"type": "string", "title": "Label", "readOnly": True}},
            ["name", "sku", "price", "label"],
        ),
    ],
)
def test_customize_pydantic_model_schema(component: str, properties: dict[str, Any], required: list[str]) -> None:
    schema = customize_pydantic_model_schema.app.openapi_schema.to_schema()

    assert schema["components"]["schemas"][component] == {
        "properties": properties,
        "type": "object",
        "required": required,
        "title": "Product",
        "description": "A product in the catalogue.",
        "examples": [{"name": "Chair", "price": 4900, "sku": "CHR-0001"}],
    }


def test_customize_pydantic_model_schema_references() -> None:
    operation = customize_pydantic_model_schema.app.openapi_schema.to_schema()["paths"]["/products"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Product-Input"
    }
    assert operation["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Product-Output"
    }


def test_customize_msgspec_model_schema() -> None:
    schema = customize_msgspec_model_schema.app.openapi_schema.to_schema()

    assert schema["paths"]["/stock"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Stock"
    }
    assert schema["components"]["schemas"] == {
        "Stock": {
            "properties": {
                "sku": {"type": "string", "pattern": "^[A-Z]{3}-[0-9]{4}$", "examples": ["CHR-0001"]},
                "quantity": {"type": "integer", "minimum": 0, "description": "Units in the warehouse"},
                "warehouse": {"anyOf": [{"type": "string"}, {"type": "null"}], "deprecated": True},
            },
            "type": "object",
            "required": ["sku", "quantity"],
            "title": "Stock",
            "description": "Stock level of a product.",
        }
    }
