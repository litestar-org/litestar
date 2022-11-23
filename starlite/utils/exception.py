from inspect import getmro
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from pydantic import BaseModel

from starlite.status_codes import HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
    from typing import Type

    from starlite.response import Response
    from starlite.types import ExceptionHandler, ExceptionHandlersMap


def get_exception_handler(exception_handlers: "ExceptionHandlersMap", exc: Exception) -> Optional["ExceptionHandler"]:
    """Given a dictionary that maps exceptions and status codes to handler functions, and an exception, returns the
    appropriate handler if existing.

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
    status_code: Optional[int] = getattr(exc, "status_code", None)
    if status_code in exception_handlers:
        return exception_handlers[status_code]  # pyright: ignore
    for cls in getmro(type(exc)):
        if cls in exception_handlers:
            return exception_handlers[cast("Type[Exception]", cls)]
    if not hasattr(exc, "status_code") and HTTP_500_INTERNAL_SERVER_ERROR in exception_handlers:
        return exception_handlers[HTTP_500_INTERNAL_SERVER_ERROR]
    return None


class ExceptionResponseContent(BaseModel):
    """Represent the contents of an exception-response."""

    status_code: int
    """Exception status code."""
    detail: str
    """Exception details or message."""
    headers: Optional[Dict[str, str]] = None
    """Headers to attach to the response."""
    extra: Optional[Union[Dict[str, Any], List[Any]]] = None
    """An extra mapping to attach to the exception."""

    def to_response(self) -> "Response":
        """Create a response from the model attributes.

        Returns:
            A response instance.
        """
        from starlite.response import Response

        return Response(
            content=self.dict(exclude_none=True, exclude={"headers"}),
            headers=self.headers,
            status_code=self.status_code,
        )


def create_exception_response(exc: Exception) -> "Response":
    """Construct a response from an exception.

    Notes:
    - For instances of [HTTPException][starlite.exceptions.HTTPException] or other exception classes that have a
        `status_code` attribute (e.g. Starlette exceptions), the status code is drawn from the exception, otherwise
        response status is `HTTP_500_INTERNAL_SERVER_ERROR`.

    Args:
        exc: An exception.

    Returns:
        Response: HTTP response constructed from exception details.
    """
    content = ExceptionResponseContent(
        status_code=getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR),
        detail=getattr(exc, "detail", repr(exc)),
        headers=getattr(exc, "headers", None),
        extra=getattr(exc, "extra", None),
    )
    return content.to_response()
