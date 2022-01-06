from asyncio import sleep
from json import loads
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from starlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse
from starlette.status import HTTP_200_OK

from starlite import File, HttpMethod, MediaType, Redirect, Response, get, route
from starlite.testing import create_test_request
from starlite.types import Stream
from tests import Person, PersonFactory


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
        FileResponse("./test_handle_request.py"),
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
