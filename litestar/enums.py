from enum import Enum

__all__ = (
    "CompressionEncoding",
    "HttpMethod",
    "MediaType",
    "OpenAPIMediaType",
    "ParamType",
    "RequestEncodingType",
    "ScopeType",
)


class HttpMethod(str, Enum):
    """An Enum for HTTP methods."""

    DELETE = "DELETE"
    """DELETE method. Defaults to return ``204 No Content``."""
    GET = "GET"
    """GET method. Defaults to return ``200 OK``."""
    HEAD = "HEAD"
    """HEAD method. Defaults to return ``200 OK``."""
    OPTIONS = "OPTIONS"
    """OPTIONS method. Defaults to return ``200 OK``."""
    PATCH = "PATCH"
    """PATCH method. Defaults to return ``200 OK``."""
    POST = "POST"
    """POST method. Defaults to return ``201 Created``."""
    PUT = "PUT"
    """PUT method. Defaults to return ``200 OK``."""


class MediaType(str, Enum):
    """An Enum for ``Content-Type`` header values."""

    JSON = "application/json"
    """JSON media type."""
    MESSAGEPACK = "application/x-msgpack"
    """MessagePack media type."""
    HTML = "text/html"
    """HTML media type."""
    TEXT = "text/plain"
    """Plain text media type."""
    CSS = "text/css"
    """CSS media type."""
    XML = "application/xml"
    """XML media type."""


class OpenAPIMediaType(str, Enum):
    """An Enum for OpenAPI specific response ``Content-Type`` header values."""

    OPENAPI_YAML = "application/vnd.oai.openapi"
    """OPENAPI_YAML media type."""
    OPENAPI_JSON = "application/vnd.oai.openapi+json"
    """OPENAPI_JSON media type."""


class RequestEncodingType(str, Enum):
    """An Enum for request ``Content-Type`` header values designating encoding formats."""

    JSON = "application/json"
    """JSON encoding."""
    MESSAGEPACK = "application/x-msgpack"
    """MessagePack encoding."""
    MULTI_PART = "multipart/form-data"
    """Multipart encoding."""
    URL_ENCODED = "application/x-www-form-urlencoded"
    """URL encoded encoding."""


class ScopeType(str, Enum):
    """An Enum for the ``http`` key stored under Scope.

    Notes:
        - ``asgi`` is used by Litestar internally and is not part of the specification.
    """

    HTTP = "http"
    """HTTP scope."""
    WEBSOCKET = "websocket"
    """Websocket scope."""
    ASGI = "asgi"
    """ASGI scope."""


class ParamType(str, Enum):
    """An Enum for the types of parameters a request can receive."""

    PATH = "path"
    """Path parameter."""
    QUERY = "query"
    """Query parameter."""
    COOKIE = "cookie"
    """Cookie parameter."""
    HEADER = "header"
    """Header parameter."""


class CompressionEncoding(str, Enum):
    """An Enum for supported compression encodings."""

    GZIP = "gzip"
    """GZIP encoding."""
    BROTLI = "br"
    """Brotli encoding."""


class ASGIExtension(str, Enum):
    """ASGI extension keys: https://asgi.readthedocs.io/en/latest/extensions.html"""

    WS_DENIAL = "websocket.http.response"
    """Websocket denial response."""
    SERVER_PUSH = "http.response.push"
    """Server push extension."""
    ZERO_COPY_SEND_EXTENSION = "http.response.zerocopysend"
    """Zero copy send extension."""
    PATH_SEND = "http.response.pathsend"
    """Path send extension."""
    TLS = "tls"
    """TLS extension."""
    EARLY_HINTS = "http.response.early_hint"
    """Early hints extension."""
    HTTP_TRAILERS = "http.response.trailers"
    """HTTP trailers extension."""
