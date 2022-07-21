from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union

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
    def __init__(self, *args: Any, detail: str = "", **kwargs: Dict[str, Any]):
        self.detail = detail
        super().__init__(*(str(arg) for arg in args if arg), detail, **kwargs)

    def __repr__(self) -> str:
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__

    def __str__(self) -> str:
        return " ".join(self.args).strip()


class MissingDependencyException(StarLiteException, ImportError):
    pass


class HTTPException(StarletteHTTPException, StarLiteException):
    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    extra: Optional[Union[Dict[str, Any], List[Any]]] = None

    def __init__(
        self,
        *args: Any,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        extra: Optional[Union[Dict[str, Any], List[Any]]] = None,
        **kwargs: Dict[str, Any],
    ):
        if not detail:
            detail = args[0] if len(args) > 0 else HTTPStatus(status_code or self.status_code).phrase
        self.extra = extra
        super().__init__(status_code or self.status_code, *args, **kwargs)  # type: ignore
        self.detail = detail
        self.args = (f"{self.status_code}: {self.detail}", *args)

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
    def __init__(self, *args: Any, template_name: str, **kwargs: Dict[str, Any]):
        super().__init__(*args, detail=f"Template {template_name} not found.", **kwargs)  # type: ignore
