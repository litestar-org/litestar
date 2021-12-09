from enum import Enum
from typing import Any, cast


class HttpMethod(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"

    @classmethod
    def is_http_method(cls, value: Any):
        """Validates that a given value is a member of the HttpMethod enum"""
        return isinstance(value, str) and value.lower() in list(cls)

    @classmethod
    def from_str(cls, value: str) -> "HttpMethod":
        if cls.is_http_method(value):
            return cast(cls, value.lower())
        raise ValueError(f"value {value} is not a supported http method")


class MediaType(str, Enum):
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
