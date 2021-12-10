import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

from starlette.requests import Request

from starlite import HttpMethod
from starlite.request import parse_query_params


def create_test_request(
    http_method: HttpMethod = HttpMethod.GET,
    query: Optional[Dict[str, Union[str, List[str]]]] = None,
    headers: Optional[Dict[str, str]] = None,
    content: Optional[Dict[str, Any]] = None,
) -> Request:
    """create a starlette request using passed in parameters"""
    scope = dict(type="http", method=http_method)
    if query:
        scope["query_string"] = urlencode(query, doseq=True)
    if headers:
        scope["headers"] = [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()]  # type: ignore
    request = Request(scope=scope)
    if content:
        request._body = json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
    return request


def test_parse_query_params():
    query = {
        "value": 10,
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": 122.53,
        "healthy": True,
        "polluting": False,
    }
    request = create_test_request(query=query)
    result = parse_query_params(request=request)
    assert result == query
