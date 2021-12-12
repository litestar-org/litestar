import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from pydantic.main import BaseModel
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite import HttpMethod, MediaType, delete, get, patch, post, put, route
from starlite.route_handlers import RouteHandler


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
def test_route_handler_param_handling(
    http_method,
    media_type,
    include_in_schema,
    response_class,
    name,
    response_headers,
    status_code,
    url,
):
    if isinstance(http_method, list) and len(http_method) == 0:
        with pytest.raises(ValidationError):
            RouteHandler(http_method=http_method)
    elif not status_code and isinstance(http_method, list) and len(http_method) > 1:
        with pytest.raises(ValidationError):
            RouteHandler(
                http_method=http_method,
                status_code=status_code,
            )
    else:
        decorator = RouteHandler(
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
def test_route_handler_default_status_code(http_method, expected_status_code):
    route_handler = RouteHandler(http_method=http_method)
    assert route_handler.status_code == expected_status_code


def test_route_handler_multiple_methods():
    with pytest.raises(ValidationError):
        RouteHandler(http_method=[HttpMethod.GET, HttpMethod.POST])
    # doesn't raise when status_code is provided
    result = route(http_method=[HttpMethod.GET, HttpMethod.POST], status_code=HTTP_200_OK)
    assert sorted(result.http_methods) == sorted([HttpMethod.GET, HttpMethod.POST])


def test_route_info_model_validation():
    with pytest.raises(ValidationError):
        RouteHandler(http_method=HttpMethod.GET, response_class=dict())


@pytest.mark.parametrize(
    "sub, http_method, expected_status_code",
    [
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
        (get, HttpMethod.GET, HTTP_200_OK),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
    ],
)
def test_route_handler_sub_classes(sub, http_method, expected_status_code):
    result = sub()(lambda x: x)
    assert result.http_method == http_method
    assert result.status_code == expected_status_code

    with pytest.raises(ValidationError):
        sub(http_method=HttpMethod.GET if http_method != HttpMethod.GET else HttpMethod.POST)
