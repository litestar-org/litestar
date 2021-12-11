from typing import List, Optional

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from pydantic.main import BaseModel
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite import HttpMethod, MediaType, delete, get, patch, post, put, route
from starlite.routing import RouteHandler


@given(
    http_method=st.sampled_from(HttpMethod),
    media_type=st.one_of(st.none(), st.sampled_from(MediaType)),
    include_in_schema=st.one_of(st.none(), st.booleans()),
    response_class=st.one_of(st.none(), st.just(Response)),
    name=st.one_of(st.none(), st.text()),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers()),
    url=st.one_of(st.none(), st.text()),
)
def test_route_info_model(
    http_method,
    media_type,
    include_in_schema,
    response_class,
    name,
    response_headers,
    status_code,
    url,
):
    RouteHandler(
        http_method=http_method,
        media_type=media_type,
        include_in_schema=include_in_schema,
        response_class=response_class,
        name=name,
        response_headers=response_headers,
        status_code=status_code,
        path=url,
    )


def test_model_function_signature():
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None):
        pass

    model = my_fn.get_signature_model()
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


def test_route_info_model_validation():
    with pytest.raises(ValidationError):
        RouteHandler(http_method=HttpMethod.GET, response_class=dict())


@given(
    http_method=st.one_of(st.sampled_from(HttpMethod), st.from_type(List[HttpMethod])),
    media_type=st.one_of(st.none(), st.sampled_from(MediaType)),
    include_in_schema=st.one_of(st.none(), st.booleans()),
    name=st.one_of(st.none(), st.text()),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers(min_value=200, max_value=204)),
    url=st.one_of(st.none(), st.text()),
)
def test_route(
    http_method,
    media_type,
    include_in_schema,
    name,
    response_class,
    response_headers,
    status_code,
    url,
):
    if isinstance(http_method, list) and len(http_method) == 0:
        with pytest.raises(ValidationError):
            route(http_method=http_method)
    elif not status_code and isinstance(http_method, list) and len(http_method) > 1:
        with pytest.raises(ValidationError):
            route(
                http_method=http_method,
                status_code=status_code,
            )
    else:
        decorator = route(
            http_method=http_method,
            media_type=media_type,
            include_in_schema=include_in_schema,
            name=name,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            path=url,
        )
        result = decorator(lambda x: x)
        if not isinstance(http_method, list) or len(http_method) > 1:
            assert result.http_method == http_method
        else:
            assert result.http_method == http_method[0]
        assert result.media_type == media_type
        assert result.include_in_schema == include_in_schema
        assert result.name == name
        assert result.response_class == response_class
        assert result.response_headers == response_headers
        assert result.path == url
        if status_code:
            assert result.status_code == status_code
        else:
            if http_method == HttpMethod.POST:
                assert result.status_code == HTTP_201_CREATED
            elif http_method == HttpMethod.DELETE:
                assert result.status_code == HTTP_204_NO_CONTENT
            else:
                assert result.status_code == HTTP_200_OK


# @pytest.mark.parametrize(
#     "http_method, expected_status_code",
#     [
#         (HttpMethod.POST, HTTP_201_CREATED),
#         (HttpMethod.DELETE, HTTP_204_NO_CONTENT),
#         (HttpMethod.GET, HTTP_200_OK),
#         (HttpMethod.PUT, HTTP_200_OK),
#         (HttpMethod.PATCH, HTTP_200_OK),
#         ([HttpMethod.POST], HTTP_201_CREATED),
#         ([HttpMethod.DELETE], HTTP_204_NO_CONTENT),
#         ([HttpMethod.GET], HTTP_200_OK),
#         ([HttpMethod.PUT], HTTP_200_OK),
#         ([HttpMethod.PATCH], HTTP_200_OK),
#     ],
# )
# def test_get_default_status_code(http_method, expected_status_code):
#     route_info = RouteHandler(http_method=http_method)
#     result = get_route_status_code(route_info)
#     assert result == expected_status_code
#
#
# def test_get_default_status_code_multiple_methods():
#     route_info = RouteHandler(http_method=[HttpMethod.GET, HttpMethod.POST])
#     with pytest.raises(ImproperlyConfiguredException):
#         get_route_status_code(route_info)
#     route_info.status_code = HTTP_200_OK
#     assert get_route_status_code(route_info) == HTTP_200_OK


@given(
    media_type=st.one_of(st.none(), st.sampled_from(MediaType)),
    include_in_schema=st.one_of(st.none(), st.booleans()),
    name=st.one_of(st.none(), st.text()),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers()),
    url=st.one_of(st.none(), st.text()),
)
def test_delete(
    media_type,
    include_in_schema,
    name,
    response_class,
    response_headers,
    status_code,
    url,
):
    decorator = delete(
        media_type=media_type,
        include_in_schema=include_in_schema,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        path=url,
    )
    result = decorator(lambda x: x)
    assert result.http_method == HttpMethod.DELETE


@given(
    media_type=st.one_of(st.none(), st.sampled_from(MediaType)),
    include_in_schema=st.one_of(st.none(), st.booleans()),
    name=st.one_of(st.none(), st.text()),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers()),
    url=st.one_of(st.none(), st.text()),
)
def test_get(
    media_type,
    include_in_schema,
    name,
    response_class,
    response_headers,
    status_code,
    url,
):
    decorator = get(
        media_type=media_type,
        include_in_schema=include_in_schema,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        path=url,
    )
    result = decorator(lambda x: x)
    assert result.http_method == HttpMethod.GET


@given(
    media_type=st.one_of(st.none(), st.sampled_from(MediaType)),
    include_in_schema=st.one_of(st.none(), st.booleans()),
    name=st.one_of(st.none(), st.text()),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers()),
    url=st.one_of(st.none(), st.text()),
)
def test_patch(
    media_type,
    include_in_schema,
    name,
    response_class,
    response_headers,
    status_code,
    url,
):
    decorator = patch(
        media_type=media_type,
        include_in_schema=include_in_schema,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        path=url,
    )
    result = decorator(lambda x: x)
    assert result.http_method == HttpMethod.PATCH


@given(
    media_type=st.one_of(st.none(), st.sampled_from(MediaType)),
    include_in_schema=st.one_of(st.none(), st.booleans()),
    name=st.one_of(st.none(), st.text()),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers()),
    url=st.one_of(st.none(), st.text()),
)
def test_post(
    media_type,
    include_in_schema,
    name,
    response_class,
    response_headers,
    status_code,
    url,
):
    decorator = post(
        media_type=media_type,
        include_in_schema=include_in_schema,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        path=url,
    )
    result = decorator(lambda x: x)
    assert result.http_method == HttpMethod.POST


@given(
    media_type=st.one_of(st.none(), st.sampled_from(MediaType)),
    include_in_schema=st.one_of(st.none(), st.booleans()),
    name=st.one_of(st.none(), st.text()),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers()),
    url=st.one_of(st.none(), st.text()),
)
def test_put(
    media_type,
    include_in_schema,
    name,
    response_class,
    response_headers,
    status_code,
    url,
):
    decorator = put(
        media_type=media_type,
        include_in_schema=include_in_schema,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        path=url,
    )
    result = decorator(lambda x: x)
    assert result.http_method == HttpMethod.PUT
