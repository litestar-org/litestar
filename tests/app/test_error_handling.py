import json

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from starlite import HTTPException, Request, Starlite


def test_handle_http_exception_handling():
    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra={"key": "value"}),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": {"key": "value"},
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        StarletteHTTPException(detail="starlite_exception", status_code=HTTP_500_INTERNAL_SERVER_ERROR),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}), AttributeError("oops")
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": repr(AttributeError("oops")),
    }
