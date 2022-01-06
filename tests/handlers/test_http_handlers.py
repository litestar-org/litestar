import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from pydantic.main import BaseModel
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_307_TEMPORARY_REDIRECT,
)

from starlite import (
    File,
    HttpMethod,
    MediaType,
    Redirect,
    delete,
    get,
    patch,
    post,
    put,
    route,
)
from starlite.exceptions import ValidationException
from starlite.handlers import HTTPRouteHandler
from starlite.response import Response


def dummy_method() -> None:
    pass


@given(
    http_method=st.sampled_from(HttpMethod),
    media_type=st.sampled_from(MediaType),
    include_in_schema=st.booleans(),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers()),
    url=st.one_of(st.none(), st.text()),
)
def test_route_handler_param_handling(
    http_method,
    media_type,
    include_in_schema,
    response_class,
    response_headers,
    status_code,
    url,
):
    if isinstance(http_method, list) and len(http_method) == 0:
        with pytest.raises(ValidationError):
            HTTPRouteHandler(http_method=http_method)
    elif not status_code and isinstance(http_method, list) and len(http_method) > 1:
        with pytest.raises(ValidationError):
            HTTPRouteHandler(
                http_method=http_method,
                status_code=status_code,
            )
    else:
        decorator = HTTPRouteHandler(
            http_method=http_method,
            media_type=media_type,
            include_in_schema=include_in_schema,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            path=url,
        )
        result = decorator(dummy_method)
        if not isinstance(http_method, list) or len(http_method) > 1:
            assert result.http_method == http_method
        else:
            assert result.http_method == http_method[0]
        assert result.media_type == media_type
        assert result.include_in_schema == include_in_schema
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
    route_handler = HTTPRouteHandler(http_method=http_method)
    assert route_handler.status_code == expected_status_code


def test_route_handler_validation_http_method():
    # doesn't raise for http methods
    for value in [*list(HttpMethod), *list(map(lambda x: x.upper(), list(HttpMethod)))]:
        assert route(http_method=value)

    # raises for invalid values
    for value in [None, "", 123, "deleze"]:
        with pytest.raises(ValidationError):
            HTTPRouteHandler(http_method=value)

    # doesn't raise when status_code is provided for multiple http_methods
    assert route(http_method=[HttpMethod.GET, HttpMethod.POST, "DELETE"], status_code=HTTP_200_OK)

    # raises otherwise
    with pytest.raises(ValidationError):
        HTTPRouteHandler(http_method=[HttpMethod.GET, HttpMethod.POST])

    # also when passing an empty list
    with pytest.raises(ValidationError):
        route(http_method=[], status_code=HTTP_200_OK)

    # also when passing malformed tokens
    with pytest.raises(ValidationError):
        route(http_method=[HttpMethod.GET, "poft"], status_code=HTTP_200_OK)


def test_route_handler_validation_response_class():
    # doesn't raise when subclass of starlette response is passed
    class SpecialResponse(Response):
        pass

    assert HTTPRouteHandler(http_method=HttpMethod.GET, response_class=SpecialResponse)

    # raises otherwise
    with pytest.raises(ValidationError):
        HTTPRouteHandler(http_method=HttpMethod.GET, response_class=dict())


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
    result = sub()(dummy_method)
    assert result.http_method == http_method
    assert result.status_code == expected_status_code

    with pytest.raises(ValidationError):
        sub(http_method=HttpMethod.GET if http_method != HttpMethod.GET else HttpMethod.POST)


def test_route_handler_function_validation():
    with pytest.raises(ValidationException):

        @get(path="/")
        def method_with_no_annotation():
            pass

    with pytest.raises(ValidationException):

        @get(path="/", status_code=HTTP_200_OK)
        def redirect_method_without_proper_status() -> Redirect:
            pass

    @get(path="/", status_code=HTTP_307_TEMPORARY_REDIRECT)
    def redirect_method() -> Redirect:
        return Redirect("/test")

    @get(path="/")
    def file_method() -> File:
        pass

    assert file_method.media_type == MediaType.TEXT
