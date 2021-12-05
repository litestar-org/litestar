from enum import Enum


class HttpMethod(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"


class MediaType(str, Enum):
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
