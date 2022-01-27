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
    HTTPRoute,
    MediaType,
    Redirect,
    Response,
    Stream,
    WebSocket,
    delete,
    get,
    patch,
    post,
    put,
    route,
)
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.handlers import HTTPRouteHandler
from starlite.testing import create_test_client
from starlite.utils import model_function_signature, normalize_path
from tests import Person, PersonFactory


def dummy_method() -> None:
    pass


@given(
    http_method=st.one_of(st.sampled_from(HttpMethod), st.lists(st.sampled_from(HttpMethod))),
    media_type=st.sampled_from(MediaType),
    include_in_schema=st.booleans(),
    response_class=st.one_of(st.none(), st.just(Response)),
    response_headers=st.one_of(st.none(), st.builds(BaseModel), st.builds(dict)),
    status_code=st.one_of(st.none(), st.integers(min_value=200, max_value=204)),
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
    if not http_method:
        with pytest.raises(ImproperlyConfiguredException):
            HTTPRouteHandler(http_method=http_method)
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
        if not url:
            assert result.paths[0] == "/"
        else:
            assert result.paths[0] == normalize_path(url)
        if isinstance(http_method, list) and len(http_method) == 1:
            http_method = http_method[0]
        if status_code:
            assert result.status_code == status_code
        elif isinstance(http_method, list):
            assert result.status_code == HTTP_200_OK
        elif http_method == HttpMethod.POST:
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
    with pytest.raises(ValidationError):
        HTTPRouteHandler(http_method="deleze")

    with pytest.raises(ImproperlyConfiguredException):
        HTTPRouteHandler(http_method=None)

    # also when passing an empty list
    with pytest.raises(ImproperlyConfiguredException):
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


@pytest.mark.asyncio
async def test_route_handler_function_validation():
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

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/test")
        def test_function_1(socket: WebSocket) -> None:
            ...

    with pytest.raises(ImproperlyConfiguredException):

        @get("/person")
        def test_function_2(self, data: Person) -> None:
            ...


@pytest.mark.asyncio
async def test_handle_to_response_async_await():
    @route(http_method=HttpMethod.POST, path="/person")
    async def test_function(data: Person) -> None:
        assert isinstance(data, Person)
        await sleep(0.1)
        return data

    person_instance = PersonFactory.build()
    test_function.signature_model = model_function_signature(test_function.fn, [])

    response = await test_function.to_response(test_function.fn(data=person_instance), [])
    assert loads(response.body) == person_instance.dict()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_response",
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
async def test_to_response_returning_redirect_starlette_response(expected_response):
    @get(path="/test")
    def test_function() -> StarletteResponse:
        return expected_response

    with create_test_client(test_function) as client:
        route: HTTPRoute = client.app.routes[0]
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(route_handler.fn(), [])
        assert isinstance(response, StarletteResponse)
        assert response is expected_response


@pytest.mark.asyncio
async def test_to_response_returning_redirect_response():
    @get(path="/test")
    def test_function() -> None:
        return Redirect(path="/somewhere-else")

    with create_test_client(test_function) as client:
        route: HTTPRoute = client.app.routes[0]
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(route_handler.fn(), [])
        assert isinstance(response, RedirectResponse)
        assert response.headers["location"] == "/somewhere-else"


@pytest.mark.asyncio
async def test_to_response_returning_file_response():
    current_file_path = Path(__file__).resolve()
    filename = Path(__file__).name

    @get(path="/test")
    def test_function() -> File:
        return File(path=current_file_path, filename=filename)

    with create_test_client(test_function) as client:
        route: HTTPRoute = client.app.routes[0]
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(route_handler.fn(), [])
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

        with create_test_client(test_function) as client:
            route: HTTPRoute = client.app.routes[0]
            route_handler = route.route_handlers[0]
            response = await route_handler.to_response(route_handler.fn(), [])
            assert isinstance(response, StreamingResponse)
    else:
        with pytest.raises(ValidationError):
            Stream(iterator=iterator)
