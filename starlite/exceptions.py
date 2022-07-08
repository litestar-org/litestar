from __future__ import annotations

from http import HTTPStatus
from typing import Any

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
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


class MissingDependencyException(StarLiteException, ImportError):
    def __init__(self, feature: str, extras: tuple[str, ...]) -> None:
        self.feature = feature
        self.extras = extras

        if len(extras) > 1:
            _extras_repr = ", ".join(map(repr, extras[:-1])) + " or " + repr(extras[-1])
        elif extras:
            _extras_repr = repr(extras[0])
        else:
            raise RuntimeError(f"`extras` argument of {self.__class__.__name__} cannot be empty.")

        detail = (
            f"To use {feature}, install starlite with {_extras_repr} extra:\n"
            f"e.g. `pip install starlite[{extras[0]}]`\n"
            f"or `poetry add starlite --extras {extras[0]}`"
        )
        super().__init__(detail)

        # this and custom Exception.__repr__ below is a workaround
        # for https://github.com/starlite-api/starlite/issues/188
        Exception.__init__(self, detail)

    __repr__ = Exception.__repr__


class HTTPException(StarLiteException, StarletteHTTPException):
    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    extra: dict[str, Any] | list[Any] | None = None

    def __init__(  # pylint: disable=super-init-not-called
        self,
        detail: str | None = None,
        status_code: int | None = None,
        extra: dict[str, Any] | list[Any] | None = None,
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


class NotAuthorizedException(HTTPException):
    status_code = HTTP_401_UNAUTHORIZED


class PermissionDeniedException(HTTPException):
    status_code = HTTP_403_FORBIDDEN


class NotFoundException(HTTPException, ValueError):
    status_code = HTTP_404_NOT_FOUND


class MethodNotAllowedException(HTTPException):
    status_code = HTTP_405_METHOD_NOT_ALLOWED


class InternalServerException(HTTPException):
    status_code = HTTP_500_INTERNAL_SERVER_ERROR


class ServiceUnavailableException(HTTPException):
    status_code = HTTP_503_SERVICE_UNAVAILABLE


class TemplateNotFound(InternalServerException):
    def __init__(self, template_name: str):
        super().__init__(detail=f"Template {template_name} not found.")
