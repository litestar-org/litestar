from inspect import Signature

from msgspec.inspect import UNSET
from pydantic.fields import Undefined

from starlite.types import Empty

DEFAULT_ALLOWED_CORS_HEADERS = {"Accept", "Accept-Language", "Content-Language", "Content-Type"}
DEFAULT_CHUNK_SIZE = 1024 * 128  # 128KB
HTTP_RESPONSE_BODY = "http.response.body"
HTTP_RESPONSE_START = "http.response.start"
ONE_MEGABYTE = 1024 * 1024
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
RESERVED_KWARGS = {"state", "headers", "cookies", "request", "socket", "data", "query", "scope", "body"}
SCOPE_STATE_DEPENDENCY_CACHE = "dependency_cache"
SCOPE_STATE_NAMESPACE = "__starlite__"
SCOPE_STATE_RESPONSE_COMPRESSED = "response_compressed"
UNDEFINED_SENTINELS = {Undefined, Signature.empty, UNSET, Empty, Ellipsis}
SKIP_VALIDATION_NAMES = {"request", "socket", "scope", "receive", "send"}
