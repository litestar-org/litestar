DEFAULT_CHUNK_SIZE = 1024  # kilo-byte
DEFAULT_ALLOWED_CORS_HEADERS = {"Accept", "Accept-Language", "Content-Language", "Content-Type"}
EXTRA_KEY_IS_DEPENDENCY = "is_dependency"
EXTRA_KEY_IS_PARAMETER = "is_parameter"
EXTRA_KEY_REQUIRED = "required"
EXTRA_KEY_SKIP_VALIDATION = "skip_validation"
EXTRA_KEY_VALUE_TYPE = "value_type"
HTTP_RESPONSE_START = "http.response.start"
HTTP_RESPONSE_BODY = "http.response.body"
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
RESERVED_KWARGS = {"state", "headers", "cookies", "request", "socket", "data", "query", "scope"}
SCOPE_STATE_DEPENDENCY_CACHE = "dependency_cache"
SCOPE_STATE_NAMESPACE = "__starlite__"
SCOPE_STATE_RESPONSE_COMPRESSED = "response_compressed"
