from __future__ import annotations

from http import HTTPStatus
from typing import Any

import pytest

from litestar import Litestar, get
from litestar.exceptions.http_exceptions import HTTPException, ValidationException
from litestar.openapi.config import OpenAPIConfig
from litestar.plugins import OpenAPISpecPlugin
from litestar.plugins.problem_details import ProblemDetailsConfig, ProblemDetailsException, ProblemDetailsPlugin
from litestar.testing import TestClient
from litestar.testing.helpers import create_test_client


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (
            ProblemDetailsException(),
            {
                "status": 500,
                "detail": HTTPStatus(500).phrase,
            },
        ),
        (
            ProblemDetailsException(status_code=400, detail="validation error", instance="https://example.net/error"),
            {
                "status": 400,
                "detail": "validation error",
                "instance": "https://example.net/error",
            },
        ),
        (
            ProblemDetailsException(
                status_code=400,
                detail="validation error",
                extra={"error": "must be positive integer", "pointer": "#age"},
            ),
            {
                "status": 400,
                "detail": "validation error",
                "error": "must be positive integer",
                "pointer": "#age",
            },
        ),
        (
            ProblemDetailsException(
                status_code=400,
                detail="validation error",
                extra=[{"error": "must be positive integer", "pointer": "#age"}],
            ),
            {
                "status": 400,
                "detail": "validation error",
                "extra": [{"error": "must be positive integer", "pointer": "#age"}],
            },
        ),
        (
            ProblemDetailsException(type_="https://example.net/validation-error"),
            {
                "type": "https://example.net/validation-error",
                "status": 500,
                "detail": HTTPStatus(500).phrase,
            },
        ),
    ],
)
def test_raising_problem_details_exception(exception: ProblemDetailsException, expected: dict[str, Any]) -> None:
    @get("/")
    async def get_foo() -> None:
        raise exception

    with create_test_client([get_foo], plugins=[ProblemDetailsPlugin()]) as client:
        response = client.get("/")

        assert response.headers["content-type"] == "application/problem+json"
        assert response.json() == expected
        assert response.status_code == expected["status"]


@pytest.mark.parametrize("enable", (True, False))
def test_enable_for_all_http_exceptions(enable: bool) -> None:
    @get("/")
    async def get_foo() -> None:
        raise HTTPException()

    config = ProblemDetailsConfig(enable_for_all_http_exceptions=enable)
    with create_test_client([get_foo], plugins=[ProblemDetailsPlugin(config)]) as client:
        response = client.get("/")

        if enable:
            assert response.headers["content-type"] == "application/problem+json"
        else:
            assert response.headers["content-type"] != "application/problem+json"


def test_exception_to_problem_detail_map() -> None:
    def validation_exception_to_problem_details_exception(exc: ValidationException) -> ProblemDetailsException:
        return ProblemDetailsException(
            type_="validation-error", detail=exc.detail, extra=exc.extra, status_code=exc.status_code
        )

    @get("/")
    async def get_foo() -> None:
        raise ValidationException(detail="Not enough balance", extra=errors)

    errors = {"accounts": ["/account/1", "/account/2"]}
    config = ProblemDetailsConfig(
        exception_to_problem_detail_map={ValidationException: validation_exception_to_problem_details_exception}
    )

    with create_test_client([get_foo], plugins=[ProblemDetailsPlugin(config)]) as client:
        response = client.get("/")

        assert response.status_code == 400
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json() == {
            "type": "validation-error",
            "status": 400,
            "detail": "Not enough balance",
            "accounts": ["/account/1", "/account/2"],
        }


def test_problem_details_plugin_is_openapi_spec_plugin() -> None:
    """``ProblemDetailsPlugin`` participates in the OpenAPI document via :class:`OpenAPISpecPlugin`."""
    plugin = ProblemDetailsPlugin()

    assert isinstance(plugin, OpenAPISpecPlugin)


def test_problem_details_plugin_contributes_schema_to_openapi_document() -> None:
    """Registering ``ProblemDetailsPlugin`` surfaces the RFC 9457 ``ProblemDetails`` schema in the served document."""
    app = Litestar(
        plugins=[ProblemDetailsPlugin()],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    with TestClient(app=app) as client:
        response = client.get("/schema/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    assert "ProblemDetails" in schemas

    schema = schemas["ProblemDetails"]
    assert schema["type"] == "object"
    properties = schema["properties"]
    assert properties["type"] == {"type": ["string", "null"], "format": "uri"}
    assert properties["title"] == {"type": ["string", "null"]}
    assert properties["status"] == {"type": "integer"}
    assert properties["detail"] == {"type": ["string", "null"]}
    assert properties["instance"] == {"type": ["string", "null"], "format": "uri"}
    assert schema["additionalProperties"] is True
