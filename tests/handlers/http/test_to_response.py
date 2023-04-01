from asyncio import sleep as async_sleep
from inspect import iscoroutine
from json import loads
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, Any, Dict, Generator, Iterator

import pytest
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.responses import Response as StarletteResponse

from starlite import HttpMethod, MediaType, Request, Response, Starlite, get, route
from starlite._signature import create_signature_model
from starlite.background_tasks import BackgroundTask
from starlite.datastructures import Cookie, ResponseHeader
from starlite.exceptions import ImproperlyConfiguredException
from starlite.response import (
    FileResponse,
    RedirectResponse,
    StreamingResponse,
    TemplateResponse,
)
from starlite.response_containers import File, Redirect, Stream, Template
from starlite.status_codes import HTTP_200_OK, HTTP_308_PERMANENT_REDIRECT
from starlite.testing import RequestFactory, create_test_client
from tests import Person, PersonFactory

if TYPE_CHECKING:
    from typing import AsyncGenerator

    from starlite.routes import HTTPRoute


def my_generator() -> Generator[str, None, None]:
    count = 0
    while True:
        count += 1
        yield str(count)


async def my_async_generator() -> "AsyncGenerator[str, None]":
    count = 0
    while True:
        count += 1
        yield str(count)


class MySyncIterator:
    def __init__(self) -> None:
        self.delay = 0.01
        self.i = 0
        self.to = 0.1

    def __iter__(self) -> Iterator[str]:
        return self

    def __next__(self) -> str:
        i = self.i
        if i >= self.to:
            raise StopAsyncIteration
        self.i += 1
        if i:
            sleep(self.delay)
        return str(i)


class MyAsyncIterator:
    def __init__(self) -> None:
        self.delay = 0.01
        self.i = 0
        self.to = 0.1

    async def __aiter__(self) -> "MyAsyncIterator":
        return self

    async def __anext__(self) -> str:
        i = self.i
        if i >= self.to:
            raise StopAsyncIteration
        self.i += 1
        if i:
            await async_sleep(self.delay)
        return str(i)


async def test_to_response_async_await(anyio_backend: str) -> None:
    @route(http_method=HttpMethod.POST, path="/person")
    async def test_function(data: Person) -> Person:
        assert isinstance(data, Person)
        return data

    person_instance = PersonFactory.build()
    test_function.signature_model = create_signature_model(
        fn=test_function.fn.value,
        plugins=[],
        preferred_validation_backend="pydantic",
        signature_namespace={},
        dependency_name_set=set(),
    )

    response = await test_function.to_response(
        data=test_function.fn.value(data=person_instance),
        plugins=[],
        app=Starlite(route_handlers=[]),
        request=RequestFactory().get(),
    )
    assert loads(response.body) == person_instance.dict()  # type: ignore


async def test_to_response_returning_starlite_response() -> None:
    @get(path="/test")
    def test_function() -> Response:
        return Response(media_type=MediaType.TEXT, content="ok")

    with create_test_client(test_function) as client:
        http_route: "HTTPRoute" = client.app.routes[0]
        route_handler = http_route.route_handlers[0]
        response = await route_handler.to_response(
            data=route_handler.fn.value(), plugins=[], app=client.app, request=RequestFactory().get()
        )
        assert isinstance(response, Response)


@pytest.mark.parametrize(
    "expected_response",
    [
        StarletteResponse(status_code=HTTP_200_OK, content=b"abc"),
        PlainTextResponse(content="abc"),
        HTMLResponse(content="<div><span/></div"),
        JSONResponse(status_code=HTTP_200_OK, content={}),
    ],
)
async def test_to_response_returning_starlette_response(
    expected_response: StarletteResponse, anyio_backend: str
) -> None:
    @get(path="/test", response_cookies=[Cookie(key="my-cookies", value="abc", path="/test")])
    def test_function() -> StarletteResponse:
        return expected_response

    with create_test_client(test_function) as client:
        http_route: "HTTPRoute" = client.app.routes[0]
        route_handler = http_route.route_handlers[0]
        response = await route_handler.to_response(
            data=route_handler.fn.value(), plugins=[], app=client.app, request=RequestFactory().get()
        )
        assert isinstance(response, StarletteResponse)
        assert response is expected_response  # type: ignore[unreachable]
        assert response.headers["set-cookie"] == "my-cookies=abc; Path=/test; SameSite=lax"


async def test_to_response_returning_redirect_response(anyio_backend: str) -> None:
    background_task = BackgroundTask(lambda: "")

    @get(
        path="/test",
        status_code=301,
        response_headers=[ResponseHeader(name="local-header", value="123")],
        response_cookies=[Cookie(key="redirect-cookie", value="aaa"), Cookie(key="general-cookie", value="xxx")],
    )
    def test_function() -> Redirect:
        return Redirect(
            path="/somewhere-else",
            headers={"response-header": "abc"},
            cookies=[Cookie(key="redirect-cookie", value="xyz")],
            background=background_task,
        )

    with create_test_client(test_function) as client:
        route: "HTTPRoute" = client.app.routes[0]
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(
            data=route_handler.fn.value(), plugins=[], app=client.app, request=RequestFactory().get()
        )
        assert isinstance(response, RedirectResponse)
        assert response.headers["location"] == "/somewhere-else"
        assert response.headers["local-header"] == "123"
        assert response.headers["response-header"] == "abc"
        cookies = response.cookies
        assert {cookie.to_header(header="") for cookie in cookies} == {
            "general-cookie=xxx; Path=/; SameSite=lax",
            "redirect-cookie=xyz; Path=/; SameSite=lax",
        }
        assert response.background == background_task


def test_to_response_returning_redirect_response_from_redirect() -> None:
    @get(path="/proxy")
    def proxy_handler() -> Dict[str, str]:
        return {"message": "redirected by before request hook"}

    def before_request_hook_handler(request: Request) -> RedirectResponse:
        return Redirect(path="/proxy").to_response(
            headers={},
            media_type="application/json",
            status_code=HTTP_308_PERMANENT_REDIRECT,
            app=request.app,
            request=request,
        )

    @get(path="/test", before_request=before_request_hook_handler)
    def redirect_handler() -> None:
        raise AssertionError("this endpoint should not be reached")

    with create_test_client(route_handlers=[redirect_handler, proxy_handler]) as client:
        response = client.get("/test")
        assert response.status_code == HTTP_200_OK, response.json()
        assert response.json() == {"message": "redirected by before request hook"}


async def test_to_response_returning_file_response(anyio_backend: str) -> None:
    current_file_path = Path(__file__).resolve()
    filename = Path(__file__).name
    background_task = BackgroundTask(lambda: "")

    @get(
        path="/test",
        response_headers=[ResponseHeader(name="local-header", value="123")],
        response_cookies=[Cookie(key="redirect-cookie", value="aaa"), Cookie(key="general-cookie", value="xxx")],
    )
    def test_function() -> File:
        return File(
            path=current_file_path,
            filename=filename,
            headers={"response-header": "abc"},
            cookies=[Cookie(key="file-cookie", value="xyz")],
            background=background_task,
        )

    with create_test_client(test_function) as client:
        route: "HTTPRoute" = client.app.routes[0]
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(
            data=route_handler.fn.value(), plugins=[], app=client.app, request=RequestFactory().get()
        )
        assert isinstance(response, FileResponse)
        assert response.file_info
        if iscoroutine(response.file_info):
            await response.file_info
        assert response.headers["local-header"] == "123"
        assert response.headers["response-header"] == "abc"
        cookies = response.cookies
        assert {cookie.to_header(header="") for cookie in cookies} == {
            "file-cookie=xyz; Path=/; SameSite=lax",
            "general-cookie=xxx; Path=/; SameSite=lax",
            "redirect-cookie=aaa; Path=/; SameSite=lax",
        }
        assert response.background == background_task


@pytest.mark.parametrize(
    "iterator, should_raise",
    [
        [my_generator(), False],
        [my_async_generator(), False],
        [MySyncIterator(), False],
        [MyAsyncIterator(), False],
        [my_generator, False],
        [my_async_generator, False],
        [MyAsyncIterator, False],
        [MySyncIterator, False],
        [[1, 2, 3, 4], False],
        ["abc", False],
        [b"abc", False],
        [{"key": 1}, False],
        [[{"key": 1}], False],
        [1, True],
        [None, True],
    ],
)
async def test_to_response_streaming_response(iterator: Any, should_raise: bool, anyio_backend: str) -> None:
    if not should_raise:
        background_task = BackgroundTask(lambda: "")

        @get(
            path="/test",
            response_headers=[ResponseHeader(name="local-header", value="123")],
            response_cookies=[Cookie(key="redirect-cookie", value="aaa"), Cookie(key="general-cookie", value="xxx")],
        )
        def test_function() -> Stream:
            return Stream(
                iterator=iterator,
                headers={"response-header": "abc"},
                cookies=[Cookie(key="streaming-cookie", value="xyz")],
                background=background_task,
            )

        with create_test_client(test_function) as client:
            route: "HTTPRoute" = client.app.routes[0]
            route_handler = route.route_handlers[0]
            response = await route_handler.to_response(
                data=route_handler.fn.value(), plugins=[], app=client.app, request=RequestFactory().get()
            )
            assert isinstance(response, StreamingResponse)
            assert response.headers["local-header"] == "123"
            assert response.headers["response-header"] == "abc"
            cookies = response.cookies
            assert {cookie.to_header(header="") for cookie in cookies} == {
                "general-cookie=xxx; Path=/; SameSite=lax",
                "redirect-cookie=aaa; Path=/; SameSite=lax",
                "streaming-cookie=xyz; Path=/; SameSite=lax",
            }
            assert response.background == background_task
    else:
        with pytest.raises(ImproperlyConfiguredException):
            Stream(iterator=iterator)


async def func_to_response_template_response(anyio_backend: str) -> None:
    background_task = BackgroundTask(lambda: "")

    @get(
        path="/test",
        response_headers=[ResponseHeader(name="local-header", value="123")],
        response_cookies=[Cookie(key="redirect-cookie", value="aaa"), Cookie(key="general-cookie", value="xxx")],
    )
    def test_function() -> Template:
        return Template(
            name="test.template",
            context={},
            headers={"response-header": "abc"},
            cookies=[Cookie(key="template-cookie", value="xyz")],
            background=background_task,
        )

    with create_test_client(test_function) as client:
        route: "HTTPRoute" = client.app.routes[0]
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(
            data=route_handler.fn.value(), plugins=[], app=client.app, request=RequestFactory().get()
        )
        assert isinstance(response, TemplateResponse)
        assert response.headers["local-header"] == "123"
        assert response.headers["response-header"] == "abc"
        cookies = response.cookies
        assert {cookie.to_header(header="") for cookie in cookies} == {
            "general-cookie=xxx; Path=/; SameSite=lax",
            "template-cookie=xyz; Path=/; SameSite=lax",
        }
        assert response.background == background_task
