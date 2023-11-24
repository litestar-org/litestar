from dataclasses import MISSING
from inspect import Signature
from typing import Final

from msgspec import UnsetType

from litestar.enums import MediaType
from litestar.types import Empty
from litestar.types.scope import (
    AcceptKey,
    BaseUrlKey,
    BodyKey,
    ContentTypeKey,
    CookiesKey,
    CsrfTokenKey,
    DependencyCacheKey,
    DoCacheKey,
    FormKey,
    HttpResponseBodyKey,
    HttpResponseStartKey,
    IsCachedKey,
    JsonKey,
    MsgpackKey,
    ParsedQueryKey,
    ResponseCompressedKey,
    UrlKey,
)

DEFAULT_ALLOWED_CORS_HEADERS: Final = {"Accept", "Accept-Language", "Content-Language", "Content-Type"}
DEFAULT_CHUNK_SIZE: Final = 1024 * 128  # 128KB
HTTP_DISCONNECT: Final = "http.disconnect"
HTTP_RESPONSE_BODY: Final = "http.response.body"
HTTP_RESPONSE_START: Final = "http.response.start"
ONE_MEGABYTE: Final = 1024 * 1024
OPENAPI_NOT_INITIALIZED: Final = "Litestar has not been instantiated with OpenAPIConfig"
REDIRECT_STATUS_CODES: Final = {301, 302, 303, 307, 308}
REDIRECT_ALLOWED_MEDIA_TYPES: Final = {MediaType.TEXT, MediaType.HTML, MediaType.JSON}
RESERVED_KWARGS: Final = {"state", "headers", "cookies", "request", "socket", "data", "query", "scope", "body"}
SKIP_VALIDATION_NAMES: Final = {"request", "socket", "scope", "receive", "send"}
UNDEFINED_SENTINELS: Final = {Signature.empty, Empty, Ellipsis, MISSING, UnsetType}
WEBSOCKET_CLOSE: Final = "websocket.close"
WEBSOCKET_DISCONNECT: Final = "websocket.disconnect"

# keys for internal stuff that we store in the "__litestar__" namespace of the scope state
SCOPE_STATE_NAMESPACE: Final = "__litestar__"

SCOPE_STATE_ACCEPT_KEY: AcceptKey = "accept"
SCOPE_STATE_BASE_URL_KEY: BaseUrlKey = "base_url"
SCOPE_STATE_BODY_KEY: BodyKey = "body"
SCOPE_STATE_CONTENT_TYPE_KEY: ContentTypeKey = "content_type"
SCOPE_STATE_COOKIES_KEY: CookiesKey = "cookies"
SCOPE_STATE_CSRF_TOKEN_KEY: CsrfTokenKey = "csrf_token"  # possible hardcoded password
SCOPE_STATE_DEPENDENCY_CACHE: DependencyCacheKey = "dependency_cache"
SCOPE_STATE_DO_CACHE: DoCacheKey = "do_cache"
SCOPE_STATE_FORM_KEY: FormKey = "form"
SCOPE_STATE_HTTP_RESPONSE_BODY_KEY: HttpResponseBodyKey = "http_response_body"
SCOPE_STATE_HTTP_RESPONSE_START_KEY: HttpResponseStartKey = "http_response_start"
SCOPE_STATE_IS_CACHED: IsCachedKey = "is_cached"
SCOPE_STATE_JSON_KEY: JsonKey = "json"
SCOPE_STATE_MSGPACK_KEY: MsgpackKey = "msgpack"
SCOPE_STATE_PARSED_QUERY_KEY: ParsedQueryKey = "parsed_query"
SCOPE_STATE_RESPONSE_COMPRESSED: ResponseCompressedKey = "response_compressed"
SCOPE_STATE_URL_KEY: UrlKey = "url"
