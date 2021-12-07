from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from pydantic.main import BaseModel
from starlette.responses import Response

from starlite import HttpMethod, MediaType
from starlite.decorators import RouteInfo, delete, get, patch, post, put, route


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
    RouteInfo(
        http_method=http_method,
        media_type=media_type,
        include_in_schema=include_in_schema,
        response_class=response_class,
        name=name,
        response_headers=response_headers,
        status_code=status_code,
        url=url,
    )


def test_route_info_model_validation():
    with pytest.raises(ValidationError):
        RouteInfo(response_class=dict())


@given(
    http_method=st.sampled_from(HttpMethod),
    media_type=st.one_of(st.none(), st.sampled_from(MediaType)),
    include_in_schema=st.one_of(st.none(), st.booleans()),
    name=st.one_of(st.none(), st.text()),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers()),
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
    decorator = route(
        http_method=http_method,
        media_type=media_type,
        include_in_schema=include_in_schema,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        url=url,
    )
    result = decorator(lambda x: x)
    route_info = cast(RouteInfo, getattr(result, "route_info"))
    assert route_info.http_method == http_method
    assert route_info.media_type == media_type
    assert route_info.include_in_schema == include_in_schema
    assert route_info.name == name
    assert route_info.response_class == response_class
    assert route_info.response_headers == response_headers
    assert route_info.status_code == status_code
    assert route_info.url == url


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
        url=url,
    )
    result = decorator(lambda x: x)
    route_info = cast(RouteInfo, getattr(result, "route_info"))
    assert route_info.http_method == HttpMethod.DELETE


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
        url=url,
    )
    result = decorator(lambda x: x)
    route_info = cast(RouteInfo, getattr(result, "route_info"))
    assert route_info.http_method == HttpMethod.GET


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
        url=url,
    )
    result = decorator(lambda x: x)
    route_info = cast(RouteInfo, getattr(result, "route_info"))
    assert route_info.http_method == HttpMethod.PATCH


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
        url=url,
    )
    result = decorator(lambda x: x)
    route_info = cast(RouteInfo, getattr(result, "route_info"))
    assert route_info.http_method == HttpMethod.POST


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
        url=url,
    )
    result = decorator(lambda x: x)
    route_info = cast(RouteInfo, getattr(result, "route_info"))
    assert route_info.http_method == HttpMethod.PUT
