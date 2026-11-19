import pytest

from litestar import Litestar, get
from litestar.exceptions import NotFoundException
from litestar.openapi import OpenAPIConfig
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromQuery
from litestar.plugins.problem_details import (
    ProblemDetails,
    ProblemDetailsConfig,
    ProblemDetailsException,
    ProblemDetailsPlugin,
)
from litestar.testing import TestClient


@get("/", raises=[NotFoundException, ProblemDetailsException], sync_to_thread=False)
def handler(value: FromQuery[int]) -> None:
    if value == 1:
        raise NotFoundException(extra={"reason": "missing"})
    raise ProblemDetailsException(
        type_="https://example.net/error", title="Error", instance="https://example.net/error/1", detail="Failed"
    )


def create_app(error_response: ResponseSpec | None) -> Litestar:
    return Litestar(
        [handler],
        openapi_config=OpenAPIConfig(title="test", version="1", error_response=error_response),
        plugins=[ProblemDetailsPlugin(ProblemDetailsConfig(enable_for_all_http_exceptions=True))],
    )


@pytest.mark.parametrize(("url", "status_code"), [("/?value=a", 400), ("/?value=1", 404), ("/?value=2", 500)])
def test_problem_details_error_response_matches_problem_details_responses(url: str, status_code: int) -> None:
    app = create_app(ResponseSpec(ProblemDetails, media_type="application/problem+json"))
    document = app.openapi_schema.to_schema()
    schema = document["components"]["schemas"]["ProblemDetails"]

    with TestClient(app) as client:
        response = client.get(url)

    assert response.status_code == status_code
    assert document["paths"]["/"]["get"]["responses"][str(status_code)]["content"] == {
        response.headers["content-type"]: {"schema": {"$ref": "#/components/schemas/ProblemDetails"}}
    }
    body = response.json()
    assert schema["required"] == ["status"]
    assert set(schema["properties"]) == {"status", "type", "title", "instance", "detail", "extra"}
    assert "additionalProperties" not in schema
    for name, value in body.items():
        if expected_type := schema["properties"].get(name, {}).get("type"):
            assert type(value) is {"integer": int, "string": str}[expected_type]


def test_plugin_does_not_change_documented_error_responses() -> None:
    app = create_app(None)

    content = app.openapi_schema.to_schema()["paths"]["/"]["get"]["responses"]["404"]["content"]
    assert set(content["application/json"]["schema"]["properties"]) == {"status_code", "detail", "extra"}
