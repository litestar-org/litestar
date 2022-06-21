from typing import Any, Dict, Type, Union

import pytest
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from starlite import InternalServerException, ValidationException
from starlite.types import ExceptionHandler
from starlite.utils.exception import get_exception_handler


def handler(_: Any, __: Any) -> Any:
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
    ],
)
def test_get_exception_handler(
    mapping: Dict[Union[int, Type[Exception]], ExceptionHandler], exc: Exception, expected: Any
) -> None:
    assert get_exception_handler(mapping, exc) == expected
