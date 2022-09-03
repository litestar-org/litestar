from inspect import getmro
from typing import TYPE_CHECKING, Dict, Optional, Type, Union, cast

from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
    from starlite.types import ExceptionHandler


def get_exception_handler(
    exception_handlers: Dict[Union[int, Type[Exception]], "ExceptionHandler"], exc: Exception
) -> Optional["ExceptionHandler"]:
    """Given a dictionary that maps exceptions and status codes to handler
    functions, and an exception, returns the appropriate handler if existing.

    Status codes are given preference over exception type.

    If no status code match exists, each class in the MRO of the exception type is checked and
    the first matching handler is returned.

    Finally, if a `500` handler is registered, it will be returned for any exception that isn't a
    subclass of `HTTPException`.

    Parameters
    ----------
    exception_handlers : dict[int | type[Exception], ExceptionHandler]
        Mapping of status codes and exception types to handlers.
    exc : Exception
        Instance to be resolved to a handler.

    Returns
    -------
    Exception | None
    """
    if not exception_handlers:
        return None
    if isinstance(exc, HTTPException) and exc.status_code in exception_handlers:
        return exception_handlers[exc.status_code]
    for cls in getmro(type(exc)):
        if cls in exception_handlers:
            return exception_handlers[cast("Type[Exception]", cls)]
    if not isinstance(exc, HTTPException) and HTTP_500_INTERNAL_SERVER_ERROR in exception_handlers:
        return exception_handlers[HTTP_500_INTERNAL_SERVER_ERROR]
    return None
