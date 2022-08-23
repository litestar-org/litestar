from enum import Enum


class HttpMethod(str, Enum):
    """An Enum for HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class MediaType(str, Enum):
    """An Enum for 'Content-Type' header values."""

    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"


class OpenAPIMediaType(str, Enum):
    """An Enum for OpenAPI specific response 'Content-Type' header values."""

    OPENAPI_YAML = "application/vnd.oai.openapi"
    OPENAPI_JSON = "application/vnd.oai.openapi+json"


class RequestEncodingType(str, Enum):
    """An Enum for request 'Content-Type' header values designating encoding
    formats."""

    JSON = "application/json"
    MULTI_PART = "multipart/form-data"
    URL_ENCODED = "application/x-www-form-urlencoded"


class ScopeType(str, Enum):
    """An Enum for the 'http' key stored under Scope.

    Notes:
        - 'asgi' is used by Starlite internally and is not part of the specification.
    """

    HTTP = "http"
    WEBSOCKET = "websocket"
    ASGI = "asgi"


class ParamType(str, Enum):
    """An Enum for the types of parameters a request can receive."""

    PATH = "path"
    QUERY = "query"
    COOKIE = "cookie"
    HEADER = "header"
