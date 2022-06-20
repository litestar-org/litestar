from inspect import isclass
from typing import Dict, Optional, Type, Union

from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from starlite.types import ExceptionHandler


def get_exception_handler(
    exception_handlers: Dict[Union[int, Type[Exception]], ExceptionHandler], exc: Exception
) -> Optional[ExceptionHandler]:
    """
    Given a dictionary that maps exceptions and status codes to handler functions,
    and an exception, returns the appropriate handler if existing.
    """
    if not exception_handlers:
        return None
    if isinstance(exc, HTTPException) and exc.status_code in exception_handlers:
        return exception_handlers[exc.status_code]
    if exc.__class__ in exception_handlers:
        return exception_handlers[exc.__class__]
    if HTTP_500_INTERNAL_SERVER_ERROR in exception_handlers:
        return exception_handlers[HTTP_500_INTERNAL_SERVER_ERROR]
    for key, value in exception_handlers.items():
        if key is Exception:
            return value
        if isclass(key) and issubclass(key, Exception) and issubclass(exc.__class__, key):
            return value
    return None
