from enum import Enum


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


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


class ScopeType(str, Enum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    ASGI = "asgi"
