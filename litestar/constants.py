from inspect import Signature
from typing import Literal

from pydantic.fields import Undefined

from litestar.enums import MediaType
from litestar.types import Empty

DEFAULT_ALLOWED_CORS_HEADERS = {"Accept", "Accept-Language", "Content-Language", "Content-Type"}
DEFAULT_CHUNK_SIZE = 1024 * 128  # 128KB
HTTP_DISCONNECT: Literal["http.disconnect"] = "http.disconnect"
HTTP_RESPONSE_BODY: Literal["http.response.body"] = "http.response.body"
HTTP_RESPONSE_START: Literal["http.response.start"] = "http.response.start"
ONE_MEGABYTE = 1024 * 1024
OPENAPI_NOT_INITIALIZED = "Litestar has not been instantiated with OpenAPIConfig"
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
REDIRECT_ALLOWED_MEDIA_TYPES = {MediaType.TEXT, MediaType.HTML}
RESERVED_KWARGS = {"state", "headers", "cookies", "request", "socket", "data", "query", "scope", "body"}
SCOPE_STATE_DEPENDENCY_CACHE: Literal["dependency_cache"] = "dependency_cache"
SCOPE_STATE_NAMESPACE: Literal["__litestar__"] = "__litestar__"
SCOPE_STATE_RESPONSE_COMPRESSED: Literal["response_compressed"] = "response_compressed"
SKIP_VALIDATION_NAMES = {"request", "socket", "scope", "receive", "send"}
UNDEFINED_SENTINELS = {Undefined, Signature.empty, Empty, Ellipsis}
WEBSOCKET_CLOSE: Literal["websocket.close"] = "websocket.close"
WEBSOCKET_DISCONNECT: Literal["websocket.disconnect"] = "websocket.disconnect"
