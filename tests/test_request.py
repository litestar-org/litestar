import json
from inspect import getfullargspec
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import pytest
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite import HttpMethod
from starlite.request import (
    get_default_status_code,
    model_function_signature,
    parse_query_params,
)


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


def test_model_function_signature():
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None):
        pass

    annotations = getfullargspec(my_fn).annotations
    model = model_function_signature(route_handler=my_fn, annotations=annotations)
    fields = model.__fields__
    assert fields.get("a").type_ == int
    assert fields.get("a").required
    assert fields.get("b").type_ == str
    assert fields.get("b").required
    assert fields.get("c").type_ == bytes
    assert not fields.get("c").required
    assert fields.get("d").type_ == bytes
    assert fields.get("d").default == b"123"
    assert fields.get("e").type_ == dict
    assert not fields.get("e").required
    assert fields.get("e").default is None


@pytest.mark.parametrize(
    "http_method, expected_status_code",
    [
        (HttpMethod.POST, HTTP_201_CREATED),
        (HttpMethod.DELETE, HTTP_204_NO_CONTENT),
        (HttpMethod.GET, HTTP_200_OK),
        (HttpMethod.PUT, HTTP_200_OK),
        (HttpMethod.PATCH, HTTP_200_OK),
    ],
)
def test_get_default_status_code(http_method, expected_status_code):
    result = get_default_status_code(http_method)
    assert result == expected_status_code
