from dataclasses import dataclass
from typing import Any

import pytest

from litestar import get, post
from litestar.exceptions import HTTPException, NotFoundException, PermissionDeniedException
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import Example
from litestar.params import FromQuery, JSONBody
from tests.unit.test_openapi.utils import build_document


@dataclass
class ErrorModel:
    code: int
    message: str


@dataclass
class ConflictModel:
    reason: str


ERROR_MODEL_REF = {"$ref": "#/components/schemas/ErrorModel"}


def get_responses(document: dict[str, Any], path: str, method: str = "get") -> dict[str, Any]:
    responses: dict[str, Any] = document["paths"][path][method]["responses"]
    return responses


def test_default_error_response_is_unchanged() -> None:
    @get("/", raises=[NotFoundException], sync_to_thread=False)
    def handler() -> None:
        return None

    document = build_document(handler)

    assert get_responses(document, "/")["404"] == {
        "description": "Nothing matches the given URI",
        "content": {
            "application/json": {
                "schema": {
                    "properties": {
                        "status_code": {"type": "integer"},
                        "detail": {"type": "string"},
                        "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                    },
                    "type": "object",
                    "required": ["detail", "status_code"],
                    "description": "Not Found Exception",
                    "examples": [{"status_code": 404, "detail": "Not Found", "extra": {}}],
                }
            }
        },
    }
    assert document["components"] == {"schemas": {}}


def test_error_response_applies_to_raises_and_validation_errors() -> None:
    @get("/raises", raises=[NotFoundException, PermissionDeniedException], sync_to_thread=False)
    def raises_handler() -> None:
        return None

    @get("/query", sync_to_thread=False)
    def query_handler(value: FromQuery[int]) -> None:
        return None

    @post("/body", sync_to_thread=False)
    def body_handler(data: JSONBody[dict[str, int]]) -> None:
        return None

    document = build_document(raises_handler, query_handler, body_handler, error_response=ResponseSpec(ErrorModel))
    content = {"application/json": {"schema": ERROR_MODEL_REF}}

    assert get_responses(document, "/raises") == {
        "200": {"description": "Request fulfilled, document follows", "headers": {}},
        "404": {"description": "Nothing matches the given URI", "content": content},
        "403": {"description": "Request forbidden -- authorization will not help", "content": content},
    }
    validation_response = {"description": "Bad request syntax or unsupported method", "content": content}
    assert get_responses(document, "/query")["400"] == validation_response
    assert get_responses(document, "/body", "post")["400"] == validation_response
    assert document["components"]["schemas"] == {
        "ErrorModel": {
            "properties": {"code": {"type": "integer"}, "message": {"type": "string"}},
            "type": "object",
            "required": ["code", "message"],
            "title": "ErrorModel",
        }
    }


def test_error_response_without_data_container_has_no_content() -> None:
    @get("/", raises=[NotFoundException], sync_to_thread=False)
    def handler() -> None:
        return None

    document = build_document(handler, error_response=ResponseSpec(None))

    assert get_responses(document, "/")["404"] == {"description": "Nothing matches the given URI"}


def test_handler_responses_take_precedence_over_error_response() -> None:
    @get(
        "/",
        raises=[NotFoundException, PermissionDeniedException],
        responses={404: ResponseSpec(ConflictModel, description="Custom not found")},
        sync_to_thread=False,
    )
    def handler() -> None:
        return None

    responses = get_responses(
        build_document(handler, error_response=ResponseSpec(ErrorModel, generate_examples=False)), "/"
    )

    assert responses["404"]["description"] == "Custom not found"
    assert responses["404"]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/ConflictModel"}
    assert responses["403"]["content"]["application/json"]["schema"] == ERROR_MODEL_REF


def test_error_response_for_exceptions_sharing_a_status_code() -> None:
    class FirstConflict(HTTPException):
        status_code = 409

    class SecondConflict(HTTPException):
        status_code = 409
        detail = "Second conflict"

    @get("/", raises=[FirstConflict, SecondConflict], sync_to_thread=False)
    def handler() -> None:
        return None

    responses = get_responses(build_document(handler, error_response=ResponseSpec(ErrorModel)), "/")

    assert responses["409"] == {
        "description": "Second conflict",
        "content": {"application/json": {"schema": ERROR_MODEL_REF}},
    }


@pytest.mark.parametrize(
    ("create_examples", "generate_examples", "expected"),
    [(False, True, False), (True, True, True), (True, False, False)],
)
def test_error_response_generates_property_examples_only_if_enabled_on_config_and_spec(
    create_examples: bool, generate_examples: bool, expected: bool
) -> None:
    @get("/", raises=[NotFoundException], sync_to_thread=False)
    def handler() -> None:
        return None

    document = build_document(
        handler,
        create_examples=create_examples,
        error_response=ResponseSpec(ErrorModel, generate_examples=generate_examples),
    )

    component = document["components"]["schemas"]["ErrorModel"]
    assert ("examples" in component) is create_examples
    assert ("examples" in component["properties"]["message"]) is expected


def test_error_response_examples() -> None:
    @get("/", raises=[NotFoundException], sync_to_thread=False)
    def handler() -> None:
        return None

    document = build_document(
        handler,
        error_response=ResponseSpec(ErrorModel, examples=[Example(value={"code": 1, "message": "Not found"})]),
    )

    assert get_responses(document, "/")["404"]["content"]["application/json"] == {
        "schema": ERROR_MODEL_REF,
        "examples": {"errormodel-example-1": {"value": {"code": 1, "message": "Not found"}}},
    }
