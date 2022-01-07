from asyncio import sleep
from json import loads
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from pydantic.main import BaseModel
from starlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse
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
    Response,
    delete,
    get,
    patch,
    post,
    put,
    route,
)
from starlite.exceptions import ValidationException
from starlite.handlers import HTTPRouteHandler
from starlite.testing import create_test_request
from starlite.types import Stream
from tests import Person, PersonFactory


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


@pytest.mark.asyncio
async def test_handle_request_async_await():
    @route(http_method=HttpMethod.POST, path="/person")
    async def test_function(data: Person) -> None:
        assert isinstance(data, Person)
        await sleep(0.1)
        return data

    person_instance = PersonFactory.build()
    request = create_test_request(content=person_instance, http_method=HttpMethod.POST)

    response = await test_function.handle_request(request=request)
    assert loads(response.body) == person_instance.dict()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        Response(status_code=HTTP_200_OK, content=b"abc", media_type=MediaType.TEXT),
        StarletteResponse(status_code=HTTP_200_OK, content=b"abc"),
        PlainTextResponse(content="abc"),
        HTMLResponse(content="<div><span/></div"),
        JSONResponse(status_code=HTTP_200_OK, content={}),
        RedirectResponse(url="/person"),
        StreamingResponse(status_code=HTTP_200_OK, content=b"abc"),
        FileResponse("./test_http_handlers.py"),
    ],
)
async def test_handle_request_when_handler_returns_starlette_responses(response):
    @get(path="/test")
    def test_function() -> StarletteResponse:
        return response

    request = create_test_request(content=None, http_method=HttpMethod.GET)
    assert await test_function.handle_request(request=request) == response


@pytest.mark.asyncio
async def test_handle_request_redirect_response():
    @get(http_method=[HttpMethod.GET], path="/test")
    def test_function() -> None:
        return Redirect(path="/somewhere-else")

    request = create_test_request(content=None, http_method=HttpMethod.GET)
    response = await test_function.handle_request(request=request)
    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == "/somewhere-else"


@pytest.mark.asyncio
async def test_handle_request_file_response():
    current_file_path = Path(__file__).resolve()
    filename = Path(__file__).name

    @get(path="/test")
    def test_function() -> File:
        return File(path=current_file_path, filename=filename)

    request = create_test_request(content=None, http_method=HttpMethod.GET)
    response = await test_function.handle_request(request=request)
    assert isinstance(response, FileResponse)
    assert response.stat_result


def my_iterator():
    count = 0
    while True:
        count += 1
        yield count


async def my_async_iterator():
    count = 0
    while True:
        count += 1
        yield count


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "iterator, should_raise", [[my_iterator(), False], [my_async_iterator(), False], [{"key": 1}, True]]
)
async def test_handle_request_streaming_response(iterator: Any, should_raise: bool):
    if not should_raise:

        @get(path="/test")
        def test_function() -> Stream:
            return Stream(iterator=iterator)

        request = create_test_request(content=None, http_method=HttpMethod.GET)
        response = await test_function.handle_request(request=request)
        assert isinstance(response, StreamingResponse)
    else:
        with pytest.raises(ValidationError):
            Stream(iterator=iterator)
