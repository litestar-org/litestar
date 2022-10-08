from inspect import getmro
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from starlite.enums import MediaType
from starlite.exceptions.http_exceptions import HTTPException
from starlite.response import Response

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

    Args:
        exception_handlers: Mapping of status codes and exception types to handlers.
        exc: Exception Instance to be resolved to a handler.

    Returns:
        Optional exception handler callable.
    """
    if not exception_handlers:
        return None
    if isinstance(exc, (StarletteHTTPException, HTTPException)) and exc.status_code in exception_handlers:
        return exception_handlers[exc.status_code]
    for cls in getmro(type(exc)):
        if cls in exception_handlers:
            return exception_handlers[cast("Type[Exception]", cls)]
    if (
        not isinstance(exc, (StarletteHTTPException, HTTPException))
        and HTTP_500_INTERNAL_SERVER_ERROR in exception_handlers
    ):
        return exception_handlers[HTTP_500_INTERNAL_SERVER_ERROR]
    return None


class ExceptionResponseContent(BaseModel):
    status_code: int
    """Exception status code."""
    detail: str
    """Exception details or message."""
    headers: Optional[Dict[str, str]] = None
    """Headers to attach to the response."""
    extra: Optional[Union[Dict[str, Any], List[Any]]] = None
    """An extra mapping to attach to the exception."""


def create_exception_response(exc: Exception) -> Response:
    """Constructs a response from an exception.

    For instances of either `starlite.exceptions.HTTPException` or `starlette.exceptions.HTTPException` the response
    status code is drawn from the exception, otherwise response status is `HTTP_500_INTERNAL_SERVER_ERROR`.

    Args:
        exc: An exception.

    Returns:
        Response: HTTP response constructed from exception details.
    """
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        content = ExceptionResponseContent(detail=exc.detail, status_code=exc.status_code)
        if isinstance(exc, HTTPException):
            content.extra = exc.extra
    else:
        content = ExceptionResponseContent(detail=repr(exc), status_code=HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(
        media_type=MediaType.JSON,
        content=content.dict(exclude_none=True),
        status_code=content.status_code,
        headers=exc.headers if isinstance(exc, (HTTPException, StarletteHTTPException)) else None,
    )
