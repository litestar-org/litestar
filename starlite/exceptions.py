from http import HTTPStatus
from typing import Optional

from pydantic.error_wrappers import ValidationError, display_errors
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR


class StarLiteException(Exception):
    def __init__(self, detail: Optional[str] = None):
        self.detail = detail
        super().__init__()

    def __repr__(self) -> str:
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__


class HTTPException(StarLiteException, StarletteHTTPException):
    def __init__(  # pylint: disable=super-init-not-called
        self,
        status_code: int,
        detail: Optional[str] = None,
    ):
        self.status_code = status_code
        self.detail = detail or HTTPStatus(status_code).phrase

    def __repr__(self) -> str:
        return f"{self.status_code} - {self.__class__.__name__} - {self.detail}"


class ImproperlyConfiguredException(HTTPException, ValueError):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=HTTP_500_INTERNAL_SERVER_ERROR)


class ValidationException(HTTPException, ValueError):
    def __init__(self, pydantic_validation_error: ValidationError, request: Request):
        detail = (
            f"Validation failed for {request.method} {request.url}: "
            f"\n\n {display_errors(pydantic_validation_error.errors())} "
        )
        super().__init__(detail=detail, status_code=HTTP_400_BAD_REQUEST)
