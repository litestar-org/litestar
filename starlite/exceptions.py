from http import HTTPStatus
from typing import Optional

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


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
        if self.detail:
            return f"{self.status_code} - {self.__class__.__name__} - {self.detail}"
        return f"{self.status_code} - {self.__class__.__name__}"


class ImproperlyConfiguredException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=HTTP_500_INTERNAL_SERVER_ERROR)
