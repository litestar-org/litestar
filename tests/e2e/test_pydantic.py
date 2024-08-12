import pydantic
from pydantic import v1 as pydantic_v1

from litestar import get, post
from litestar.testing import create_test_client


def test_app_with_v1_and_v2_models() -> None:
    class ModelV1(pydantic.v1.BaseModel):  # pyright: ignore
        foo: str

    class ModelV2(pydantic.BaseModel):
        foo: str

    @get("/v1")
    def handler_v1() -> ModelV1:
        return ModelV1(foo="bar")

    @get("/v2")
    def handler_v2() -> ModelV2:
        return ModelV2(foo="bar")

    with create_test_client([handler_v1, handler_v2]) as client:
        assert client.get("/v1").json() == {"foo": "bar"}
        assert client.get("/v2").json() == {"foo": "bar"}


def test_pydantic_v1_model_with_field_default() -> None:
    # https://github.com/litestar-org/litestar/issues/3471

    class TestDto(pydantic_v1.BaseModel):
        test_str: str = pydantic_v1.Field(default="some_default", max_length=100)

    @post(path="/test")
    async def test(data: TestDto) -> str:
        return "success"

    with create_test_client(route_handlers=[test]) as client:
        response = client.get("/schema/openapi.json")
        assert response.status_code == 200
        assert response.json() == {
            "components": {
                "schemas": {
                    "test_pydantic_v1_model_with_field_default.TestDto": {
                        "properties": {"test_str": {"default": "some_default", "maxLength": 100, "type": "string"}},
                        "required": [],
                        "title": "TestDto",
                        "type": "object",
                    }
                }
            },
            "info": {"title": "Litestar API", "version": "1.0.0"},
            "openapi": "3.1.0",
            "paths": {
                "/test": {
                    "post": {
                        "deprecated": False,
                        "operationId": "TestTest",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/test_pydantic_v1_model_with_field_default.TestDto"
                                    }
                                }
                            },
                            "required": True,
                        },
                        "responses": {
                            "201": {
                                "content": {"text/plain": {"schema": {"type": "string"}}},
                                "description": "Document " "created, " "URL " "follows",
                                "headers": {},
                            },
                            "400": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "description": "Validation " "Exception",
                                            "examples": [{"detail": "Bad " "Request", "extra": {}, "status_code": 400}],
                                            "properties": {
                                                "detail": {"type": "string"},
                                                "extra": {
                                                    "additionalProperties": {},
                                                    "type": ["null", "object", "array"],
                                                },
                                                "status_code": {"type": "integer"},
                                            },
                                            "required": ["detail", "status_code"],
                                            "type": "object",
                                        }
                                    }
                                },
                                "description": "Bad " "request " "syntax or " "unsupported " "method",
                            },
                        },
                        "summary": "Test",
                    }
                }
            },
            "servers": [{"url": "/"}],
        }
