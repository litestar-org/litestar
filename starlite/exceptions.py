from http import HTTPStatus
from typing import Any, Dict, Optional

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)


class StarLiteException(Exception):
    def __init__(self, detail: str = ""):
        self.detail = detail
        super().__init__()

    def __repr__(self) -> str:
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__


class HTTPException(StarLiteException, StarletteHTTPException):
    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    extra: Optional[Dict[str, Any]] = None

    def __init__(  # pylint: disable=super-init-not-called
        self, detail: Optional[str] = None, status_code: Optional[int] = None, extra: Optional[Dict[str, Any]] = None
    ):
        if status_code:
            self.status_code = status_code
        self.detail = detail or HTTPStatus(self.status_code).phrase
        self.extra = extra

    def __repr__(self) -> str:
        return f"{self.status_code} - {self.__class__.__name__} - {self.detail}"


class ImproperlyConfiguredException(HTTPException, ValueError):
    pass


class ValidationException(HTTPException, ValueError):
    status_code = HTTP_400_BAD_REQUEST


class NotFoundException(HTTPException, ValueError):
    status_code = HTTP_404_NOT_FOUND


class NotAuthorizedException(HTTPException):
    status_code = HTTP_401_UNAUTHORIZED


class PermissionDeniedException(HTTPException):
    status_code = HTTP_403_FORBIDDEN


class InternalServerException(HTTPException):
    status_code = HTTP_500_INTERNAL_SERVER_ERROR


class ServiceUnavailableException(HTTPException):
    status_code = HTTP_503_SERVICE_UNAVAILABLE
