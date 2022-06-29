import json
from typing import Any

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from starlite import HTTPException, Request
from starlite.middleware import ExceptionHandlerMiddleware


def test_default_handle_http_exception_handling() -> None:
    async def dummy_app(scope: Any, receive: Any, send: Any) -> None:
        return None

    middleware = ExceptionHandlerMiddleware(dummy_app, False, {})

    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra={"key": "value"}),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": {"key": "value"},
        "status_code": 500,
    }

    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception"),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": None,
        "status_code": 500,
    }

    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra=None),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": None,
        "status_code": 500,
    }

    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra=["extra-1", "extra-2"]),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": ["extra-1", "extra-2"],
        "status_code": 500,
    }

    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        StarletteHTTPException(detail="starlite_exception", status_code=HTTP_500_INTERNAL_SERVER_ERROR),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
    }

    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}), AttributeError("oops")
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": repr(AttributeError("oops")),
    }
