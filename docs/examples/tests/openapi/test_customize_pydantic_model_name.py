from examples.openapi import customize_pydantic_model_name
from starlite.testing import TestClient


def test_schema_generation() -> None:
    with TestClient(app=customize_pydantic_model_name.app) as client:
        assert client.app.openapi_schema.dict(exclude_none=True) == {
            "openapi": "3.1.0",
            "info": {"title": "Starlite API", "version": "1.0.0"},
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
                                    "application/json": {
                                        "media_type_schema": {"ref": "#/components/schemas/IdContainer"}
                                    }
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
                        "properties": {"id": {"type": "string", "schema_format": "uuid", "title": "Id"}},
                        "type": "object",
                        "required": ["id"],
                        "title": "IdContainer",
                    }
                }
            },
        }
