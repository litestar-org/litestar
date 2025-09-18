from docs.examples.openapi import customize_openapi_types, customize_pydantic_model_name

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
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/IdModel"}}},
                            }
                        },
                        "deprecated": False,
                    }
                }
            },
            "components": {
                "schemas": {
                    "IdModel": {
                        "properties": {"id": {"type": "string", "format": "uuid"}},
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
