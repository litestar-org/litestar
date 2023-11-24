from __future__ import annotations

from typing import Literal

AcceptKey = Literal["accept"]
BaseUrlKey = Literal["base_url"]
BodyKey = Literal["body"]
ContentTypeKey = Literal["content_type"]
CookiesKey = Literal["cookies"]
CsrfTokenKey = Literal["csrf_token"]
DependencyCacheKey = Literal["dependency_cache"]
DoCacheKey = Literal["do_cache"]
FormKey = Literal["form"]
HttpResponseBodyKey = Literal["http_response_body"]
HttpResponseStartKey = Literal["http_response_start"]
IsCachedKey = Literal["is_cached"]
JsonKey = Literal["json"]
MsgpackKey = Literal["msgpack"]
ParsedQueryKey = Literal["parsed_query"]
ResponseCompressedKey = Literal["response_compressed"]
UrlKey = Literal["url"]

ScopeStateKeyType = Literal[
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
]
