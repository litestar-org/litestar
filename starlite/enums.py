from enum import Enum
from typing import Any, cast

from starlite.exceptions import ImproperlyConfiguredException


class HttpMethod(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"

    @classmethod
    def is_http_method(cls, value: Any) -> bool:
        """Validates that a given value is a member of the HttpMethod enum"""
        return isinstance(value, str) and value.lower() in list(cls)

    @classmethod
    def from_str(cls, value: Any) -> "HttpMethod":
        """Given a string value, return an enum member or raise a ValueError"""
        if cls.is_http_method(value):
            return cast(HttpMethod, value.lower())
        raise ImproperlyConfiguredException(f"value {value} is not a supported http method")


class MediaType(str, Enum):
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"


class OpenAPIMediaType(str, Enum):
    OPENAPI_YAML = "application/vnd.oai.openapi"
    OPENAPI_JSON = "application/vnd.oai.openapi+json"


class RequestEncodingType(str, Enum):
    JSON = "application/json"
    MULTI_PART = "multipart/form-data"
    URL_ENCODED = "application/x-www-form-urlencoded"
