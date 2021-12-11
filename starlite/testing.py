from json import dumps
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

from pydantic import BaseModel
from starlette.requests import Request

from starlite.enums import HttpMethod


def create_test_request(
    http_method: HttpMethod = HttpMethod.GET,
    scheme: str = "http",
    server: str = "test.org",
    port: int = 3000,
    root_path: str = "/",
    path: str = "",
    query: Optional[Dict[str, Union[str, List[str]]]] = None,
    headers: Optional[Dict[str, str]] = None,
    content: Optional[Union[Dict[str, Any], BaseModel]] = None,
) -> Request:
    """Create a starlette request using passed in parameters"""
    scope = dict(
        type="http",
        method=http_method,
        scheme=scheme,
        server=(server, port),
        root_path=root_path,
        path=path,
        headers=[],
    )
    if query:
        scope["query_string"] = urlencode(query, doseq=True)
    if headers:
        scope["headers"] = [
            (key.lower().encode("latin-1", errors="ignore"), value.encode("latin-1", errors="ignore"))
            for key, value in headers.items()
        ]
    request = Request(scope=scope)
    if content:
        if isinstance(content, BaseModel):
            request._body = content.json().encode("utf-8")
        else:
            request._body = dumps(
                content,
                ensure_ascii=False,
                allow_nan=False,
                indent=None,
                separators=(",", ":"),
            ).encode("utf-8")
    return request
