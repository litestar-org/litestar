from inspect import getmro
from typing import Dict, Optional, Type, Union, cast

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
    if type(exc) in exception_handlers:
        return exception_handlers[type(exc)]
    if HTTP_500_INTERNAL_SERVER_ERROR in exception_handlers:
        return exception_handlers[HTTP_500_INTERNAL_SERVER_ERROR]
    for cls in getmro(type(exc)):
        if cls in exception_handlers:
            return exception_handlers[cast(Type[Exception], cls)]
    return None
