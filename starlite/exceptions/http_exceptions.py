from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from starlite.exceptions.base_exceptions import StarLiteException


class HTTPException(StarletteHTTPException, StarLiteException):
    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR
    """Exception status code."""
    detail: str
    """Exception details or message."""
    headers: Optional[Dict[str, str]]
    """Headers to attach to the response."""
    extra: Optional[Union[Dict[str, Any], List[Any]]]
    """An extra mapping to attach to the exception."""

    def __init__(
        self,
        *args: Any,
        detail: str = "",
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        extra: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> None:
        """Base exception for HTTP error responses.

        These exceptions carry information to construct an HTTP response.

        Args:
            *args: if `detail` kwarg not provided, first arg should be error detail.
            detail: Exception details or message. Will default to args[0] if not provided.
            status_code: Exception HTTP status code.
            headers: Headers to set on the response.
            extra: An extra mapping to attach to the exception.
        """

        super().__init__(status_code or self.status_code)

        if not detail:
            detail = args[0] if args else HTTPStatus(self.status_code).phrase
            args = args[1:]

        self.extra = extra
        self.detail = detail
        self.headers = headers
        self.args = (f"{self.status_code}: {self.detail}", *args)

    def __repr__(self) -> str:
        return f"{self.status_code} - {self.__class__.__name__} - {self.detail}"


class ImproperlyConfiguredException(HTTPException, ValueError):
    """Application has improper configuration."""


class ValidationException(HTTPException, ValueError):
    """Client error."""

    status_code = HTTP_400_BAD_REQUEST


class NotAuthorizedException(HTTPException):
    """Request lacks valid authentication credentials for the requested
    resource."""

    status_code = HTTP_401_UNAUTHORIZED


class PermissionDeniedException(HTTPException):
    """Request understood, but not authorized."""

    status_code = HTTP_403_FORBIDDEN


class NotFoundException(HTTPException, ValueError):
    """Cannot find the requested resource."""

    status_code = HTTP_404_NOT_FOUND


class MethodNotAllowedException(HTTPException):
    """Server knows the request method, but the target resource doesn't support
    this method."""

    status_code = HTTP_405_METHOD_NOT_ALLOWED


class TooManyRequestsException(HTTPException):
    """Request limits have been exceeded."""

    status_code = HTTP_429_TOO_MANY_REQUESTS


class InternalServerException(HTTPException):
    """Server encountered an unexpected condition that prevented it from
    fulfilling the request."""

    status_code = HTTP_500_INTERNAL_SERVER_ERROR


class ServiceUnavailableException(HTTPException):
    """Server is not ready to handle the request."""

    status_code = HTTP_503_SERVICE_UNAVAILABLE


class TemplateNotFoundException(InternalServerException):
    def __init__(self, *args: Any, template_name: str) -> None:
        """Referenced template could not be found.

        Args:
            *args (Any): Passed through to `super().__init__()` - should not include `detail`.
            template_name (str): Name of template that could not be found.
        """
        super().__init__(*args, detail=f"Template {template_name} not found.")
