from typing import Any

import pytest

from starlite.exceptions import (
    HTTPException,
    InternalServerException,
    ValidationException,
)
from starlite.middleware.exceptions.middleware import get_exception_handler
from starlite.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from starlite.types import ExceptionHandlersMap


def handler(_: Any, __: Any) -> Any:
    return None


def handler_2(_: Any, __: Any) -> Any:
    return None


@pytest.mark.parametrize(
    ["mapping", "exc", "expected"],
    [
        ({}, Exception, None),
        ({HTTP_400_BAD_REQUEST: handler}, ValidationException(), handler),
        ({InternalServerException: handler}, InternalServerException(), handler),
        ({HTTP_500_INTERNAL_SERVER_ERROR: handler}, Exception(), handler),
        ({TypeError: handler}, TypeError(), handler),
        ({Exception: handler}, ValidationException(), handler),
        ({ValueError: handler}, ValidationException(), handler),
        ({ValidationException: handler}, Exception(), None),
        ({HTTP_500_INTERNAL_SERVER_ERROR: handler}, ValidationException(), None),
        ({HTTP_500_INTERNAL_SERVER_ERROR: handler, HTTPException: handler_2}, ValidationException(), handler_2),
        ({HTTPException: handler, ValidationException: handler_2}, ValidationException(), handler_2),
        ({HTTPException: handler, ValidationException: handler_2}, InternalServerException(), handler),
        ({HTTP_500_INTERNAL_SERVER_ERROR: handler, HTTPException: handler_2}, InternalServerException(), handler),
    ],
)
def test_get_exception_handler(mapping: ExceptionHandlersMap, exc: Exception, expected: Any) -> None:
    assert get_exception_handler(mapping, exc) == expected
