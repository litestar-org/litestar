from asyncio import sleep as async_sleep
from json import loads
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, Any, AsyncIterator, Generator, Iterator

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

from starlite import (
    Cookie,
    File,
    HttpMethod,
    HTTPRoute,
    MediaType,
    Redirect,
    Response,
    ResponseHeader,
    Request,
    Stream,
    Template,
    get,
    route,
)
from starlite.datastructures import BackgroundTask
from starlite.response import TemplateResponse
from starlite.signature import SignatureModelFactory
from starlite.testing import create_test_client
from tests import Person, PersonFactory

if TYPE_CHECKING:
    from typing import AsyncGenerator


@pytest.mark.asyncio()
async def test_to_response_async_await() -> None:
    @route(http_method=HttpMethod.POST, path="/person")
    async def test_function(data: Person) -> Person:
        assert isinstance(data, Person)
        return data

    person_instance = PersonFactory.build()
    test_function.signature_model = SignatureModelFactory(
        test_function.fn, [], set()  # type:ignore[arg-type]
    ).create_signature_model()

    response = await test_function.to_response(
        data=test_function.fn(data=person_instance), plugins=[], app=None  # type: ignore
    )
    assert loads(response.body) == person_instance.dict()


async def slow_numbers(minimum: int, maximum: int) -> Any:
    yield "<html><body><ul>"
    for number in range(minimum, maximum + 1):
        yield "<li>%d</li>" % number
    yield "</ul></body></html>"


generator = slow_numbers(1, 10)


async def test_to_response_returning_starlite_response() -> None:
    @get(path="/test")
    def test_function() -> Response:
        return Response(status_code=HTTP_200_OK, media_type=MediaType.TEXT, content="ok")

    with create_test_client(test_function) as client:
        http_route: HTTPRoute = client.app.routes[0]  # type: ignore
        route_handler = http_route.route_handlers[0]
        response = await route_handler.to_response(data=route_handler.fn(), plugins=[], app=None)  # type: ignore
        assert isinstance(response, Response)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "expected_response",
    [
        Response(status_code=HTTP_200_OK, content=b"abc", media_type=MediaType.TEXT),
        StarletteResponse(status_code=HTTP_200_OK, content=b"abc"),
        PlainTextResponse(content="abc"),
        HTMLResponse(content="<div><span/></div"),
        JSONResponse(status_code=HTTP_200_OK, content={}),
        RedirectResponse(url="/person"),
        StreamingResponse(status_code=HTTP_200_OK, content=generator),
        FileResponse("./test_to_response.py"),
    ],
)
async def test_to_response_returning_redirect_starlette_response(expected_response: StarletteResponse) -> None:
    @get(path="/test")
    def test_function() -> StarletteResponse:
        return expected_response

    with create_test_client(test_function) as client:
        http_route: HTTPRoute = client.app.routes[0]  # type: ignore
        route_handler = http_route.route_handlers[0]
        response = await route_handler.to_response(data=route_handler.fn(), plugins=[], app=None)  # type: ignore
        assert isinstance(response, StarletteResponse)
        assert response is expected_response


@pytest.mark.asyncio()
async def test_to_response_returning_redirect_response() -> None:
    background_task = BackgroundTask(lambda: "")

    @get(
        path="/test",
        status_code=301,
        response_headers={"local-header": ResponseHeader(value="123")},
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
        route: HTTPRoute = client.app.routes[0]  # type: ignore
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(data=route_handler.fn(), plugins=[], app=None)  # type: ignore
        assert isinstance(response, RedirectResponse)
        assert response.headers["location"] == "/somewhere-else"
        assert response.headers["local-header"] == "123"
        assert response.headers["response-header"] == "abc"
        cookies = response.headers.getlist("set-cookie")
        assert len(cookies) == 2
        assert cookies[0] == "redirect-cookie=xyz; Path=/; SameSite=lax"
        assert cookies[1] == "general-cookie=xxx; Path=/; SameSite=lax"
        assert response.background == background_task


@pytest.mark.xfail
def test_to_response_returning_redirect_response_from_redirect() -> None:
    @get(
        path="/proxy",
    )
    def proxy() -> str:
        return "redirected by before request hook"

    def request_hook(request: Request) -> RedirectResponse:

        return Redirect(
            path="https://app.example.com"
        ).to_response(headers={}, media_type="application/json", status_code=308, app=request.app)

    @get(
        path="/test",
        before_request=request_hook
    )
    def handler() -> None:
        ...

    with create_test_client(route_handlers=[handler, proxy]) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == "redirected by before request hook"


@pytest.mark.asyncio()
async def test_to_response_returning_file_response() -> None:
    current_file_path = Path(__file__).resolve()
    filename = Path(__file__).name
    background_task = BackgroundTask(lambda: "")

    @get(
        path="/test",
        response_headers={"local-header": ResponseHeader(value="123")},
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
        route: HTTPRoute = client.app.routes[0]  # type: ignore
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(data=route_handler.fn(), plugins=[], app=None)  # type: ignore
        assert isinstance(response, FileResponse)
        assert response.stat_result
        assert response.path == current_file_path
        assert response.filename == filename
        assert response.headers["local-header"] == "123"
        assert response.headers["response-header"] == "abc"
        cookies = response.headers.getlist("set-cookie")
        assert len(cookies) == 3
        assert cookies[0] == "file-cookie=xyz; Path=/; SameSite=lax"
        assert cookies[1] == "general-cookie=xxx; Path=/; SameSite=lax"
        assert response.background == background_task


def my_generator() -> Generator[int, None, None]:
    count = 0
    while True:
        count += 1
        yield count


async def my_async_generator() -> "AsyncGenerator[int, None]":
    count = 0
    while True:
        count += 1
        yield count


class MySyncIterator:
    def __init__(self) -> None:
        self.delay = 0.01
        self.i = 0
        self.to = 0.1

    def __iter__(self) -> Iterator[int]:
        return self

    def __next__(self) -> int:
        i = self.i
        if i >= self.to:
            raise StopAsyncIteration
        self.i += 1
        if i:
            sleep(self.delay)
        return i


class MyAsyncIterator:
    def __init__(self) -> None:
        self.delay = 0.01
        self.i = 0
        self.to = 0.1

    def __aiter__(self) -> AsyncIterator[int]:
        return self

    async def __anext__(self) -> int:
        i = self.i
        if i >= self.to:
            raise StopAsyncIteration
        self.i += 1
        if i:
            await async_sleep(self.delay)
        return i


@pytest.mark.asyncio()
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
        [{"key": 1}, True],
    ],
)
async def test_to_response_streaming_response(iterator: Any, should_raise: bool) -> None:
    if not should_raise:
        background_task = BackgroundTask(lambda: "")

        @get(
            path="/test",
            response_headers={"local-header": ResponseHeader(value="123")},
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
            route: HTTPRoute = client.app.routes[0]  # type: ignore
            route_handler = route.route_handlers[0]
            response = await route_handler.to_response(data=route_handler.fn(), plugins=[], app=None)  # type: ignore
            assert isinstance(response, StreamingResponse)
            assert response.headers["local-header"] == "123"
            assert response.headers["response-header"] == "abc"
            cookies = response.headers.getlist("set-cookie")
            assert len(cookies) == 3
            assert cookies[0] == "streaming-cookie=xyz; Path=/; SameSite=lax"
            assert cookies[1] == "general-cookie=xxx; Path=/; SameSite=lax"
            assert response.background == background_task
    else:
        with pytest.raises(ValidationError):
            Stream(iterator=iterator)


@pytest.mark.asyncio()
async def func_to_response_template_response() -> None:
    background_task = BackgroundTask(lambda: "")

    @get(
        path="/test",
        response_headers={"local-header": ResponseHeader(value="123")},
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
        route: HTTPRoute = client.app.routes[0]  # type: ignore
        route_handler = route.route_handlers[0]
        response = await route_handler.to_response(data=route_handler.fn(), plugins=[], app=None)  # type: ignore
        assert isinstance(response, TemplateResponse)
        assert response.headers["local-header"] == "123"
        assert response.headers["response-header"] == "abc"
        cookies = response.headers.getlist("set-cookie")
        assert len(cookies) == 2
        assert cookies[0] == "template-cookie=xyz; Path=/; SameSite=lax"
        assert cookies[1] == "general-cookie=xxx; Path=/; SameSite=lax"
        assert response.background == background_task
