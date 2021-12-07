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


def test_fuzz_parse_query_params():
    query = {"value": 10, "veggies": ["tomato", "potato", "aubergine"], "calories": 122.53, "healthy": True}
    request = create_test_request(query=query)
    result = parse_query_params(request=request)
    assert result == query


# @given(route_handler=st.builds(RouteHandler), request=st.from_type(Request))
# def test_fuzz_get_http_handler_parameters(route_handler, request):
#     get_http_handler_parameters(route_handler=route_handler, request=request)
#
#
# @given(route_handler=st.builds(RouteHandler), request=st.from_type(Request))
# def test_fuzz_handle_request(route_handler, request):
#     handle_request(route_handler=route_handler, request=request)
#
#
# @given(
#     route_handler=st.builds(RouteHandler),
#     annotations=st.dictionaries(keys=st.text(), values=st.builds(object)),
# )
# def test_fuzz_model_function_signature(route_handler, annotations):
#     model_function_signature(route_handler=route_handler, annotations=annotations)
#
