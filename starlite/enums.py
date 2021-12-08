from enum import Enum
from typing import Any


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


class MediaType(str, Enum):
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
