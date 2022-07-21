from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR  # noqa: TC002

from starlite.enums import MediaType
from starlite.response import Response

from .exceptions import HTTPException

__all__ = ["create_exception_response"]


class ExceptionResponseContent(BaseModel):
    detail: Optional[str]
    extra: Optional[Union[Dict[str, Any], List[Any]]]
    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR


def create_exception_response(exc: Exception) -> Response:
    """
    Constructs a response from an exception.

    For instances of either `starlite.exceptions.HTTPException` or `starlette.exceptions.HTTPException` the response
    status code is drawn from the exception, otherwise response status is `HTTP_500_INTERNAL_SERVER_ERROR`.

    Args:
        exc (Exception): Any exception.

    Returns:
        Response
    """
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        content = ExceptionResponseContent(detail=exc.detail, status_code=exc.status_code)
        if isinstance(exc, HTTPException):
            content.extra = exc.extra
    else:
        content = ExceptionResponseContent(detail=repr(exc))
    return Response(
        media_type=MediaType.JSON,
        content=content.dict(exclude_none=True),
        status_code=content.status_code,
    )
