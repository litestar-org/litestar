from __future__ import annotations

from http import HTTPStatus
from typing import Any

import pytest

from litestar import get
from litestar.exceptions.http_exceptions import HTTPException, ValidationException
from litestar.plugins.problem_details import ProblemDetailsConfig, ProblemDetailsException, ProblemDetailsPlugin
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
