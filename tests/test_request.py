import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import pytest
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite import HttpMethod, ImproperlyConfiguredException
from starlite.request import get_route_status_code, parse_query_params
from starlite.routing import RouteHandler


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


@pytest.mark.parametrize(
    "http_method, expected_status_code",
    [
        (HttpMethod.POST, HTTP_201_CREATED),
        (HttpMethod.DELETE, HTTP_204_NO_CONTENT),
        (HttpMethod.GET, HTTP_200_OK),
        (HttpMethod.PUT, HTTP_200_OK),
        (HttpMethod.PATCH, HTTP_200_OK),
        ([HttpMethod.POST], HTTP_201_CREATED),
        ([HttpMethod.DELETE], HTTP_204_NO_CONTENT),
        ([HttpMethod.GET], HTTP_200_OK),
        ([HttpMethod.PUT], HTTP_200_OK),
        ([HttpMethod.PATCH], HTTP_200_OK),
    ],
)
def test_get_default_status_code(http_method, expected_status_code):
    route_info = RouteHandler(http_method=http_method)
    result = get_route_status_code(route_info)
    assert result == expected_status_code


def test_get_default_status_code_multiple_methods():
    route_info = RouteHandler(http_method=[HttpMethod.GET, HttpMethod.POST])
    with pytest.raises(ImproperlyConfiguredException):
        get_route_status_code(route_info)
    route_info.status_code = HTTP_200_OK
    assert get_route_status_code(route_info) == HTTP_200_OK
