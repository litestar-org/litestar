from http import HTTPStatus
from typing import Optional

from starlette.exceptions import HTTPException as StarletteHTTPException


class StarLiteException(Exception):
    def __init__(self, message: Optional[str] = None):
        self.message = message
        super().__init__()

    def __repr__(self) -> str:
        if self.message:
            return f"{self.__class__.__name__} - {self.message}"
        return self.__class__.__name__


class HTTPException(StarLiteException, StarletteHTTPException):
    def __init__(
        self,
        status_code: int,
        message: Optional[str] = None,
    ):
        self.status_code = status_code
        super().__init__(message or HTTPStatus(status_code).phrase)

    def __repr__(self) -> str:
        if self.message:
            return f"{self.status_code} - {self.__class__.__name__} - {self.message}"
        return f"{self.status_code} - {self.__class__.__name__}"


class ConfigurationException(StarLiteException):
    pass
