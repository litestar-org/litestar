"""The tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are
meant to ensure our compatibility with their API.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import anyio
import pytest

from starlite import ImproperlyConfiguredException, MediaType
from starlite.connection import Request
from starlite.datastructures import BackgroundTask
from starlite.response import (
    FileResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from starlite.status_codes import HTTP_200_OK
from starlite.testing import TestClient

if TYPE_CHECKING:
    from starlite.types import Message, Receive, Scope, Send


def test_text_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = Response("hello, world", media_type="text/plain")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.text == "hello, world"


def test_bytes_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = Response(b"xxxxx", media_type="image/png")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.content == b"xxxxx"


def test_json_none_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = Response(content=None)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.json() is None
    assert response.content == b"null"


def test_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = Response("hello, world", media_type="text/plain")
        else:
            response = RedirectResponse("/")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/redirect")
    assert response.text == "hello, world"
    assert response.url == "http://testserver/"


def test_quoting_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/test/":
            response = Response("hello, world", media_type="text/plain")
        else:
            response = RedirectResponse(url="/test/")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/redirect", follow_redirects=True)
    assert response.text == "hello, world"
    assert str(response.url) == "http://testserver/test/"


def test_redirect_response_content_length_header() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = Response("hello", media_type="text/plain")  # pragma: nocover
        else:
            response = RedirectResponse("/")
        await response(scope, receive, send)

    client: TestClient = TestClient(app)  # type: ignore
    response = client.request("GET", "/redirect", allow_redirects=False)
    assert response.url == "http://testserver/redirect"
    assert "content-length" not in response.headers


def test_streaming_response() -> None:
    filled_by_bg_task = ""

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        async def numbers(minimum, maximum) -> None:
            for i in range(minimum, maximum + 1):
                yield str(i)
                if i != maximum:
                    yield ", "
                await anyio.sleep(0)

        async def numbers_for_cleanup(start=1, stop=5) -> None:
            nonlocal filled_by_bg_task
            async for thing in numbers(start, stop):
                filled_by_bg_task = filled_by_bg_task + thing

        cleanup_task = BackgroundTask(numbers_for_cleanup, start=6, stop=9)
        generator = numbers(1, 5)
        response = StreamingResponse(generator, media_type="text/plain", background=cleanup_task)
        await response(scope, receive, send)

    assert filled_by_bg_task == ""
    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.text == "1, 2, 3, 4, 5"
    assert filled_by_bg_task == "6, 7, 8, 9"


def test_streaming_response_custom_iterator() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        class CustomAsyncIterator:
            def __init__(self):
                self._called = 0

            def __aiter__(self):
                return self

            async def __anext__(self) -> None:
                if self._called == 5:
                    raise StopAsyncIteration()
                self._called += 1
                return str(self._called)

        response = StreamingResponse(CustomAsyncIterator(), media_type="text/plain")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.text == "12345"


def test_streaming_response_custom_iterable() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        class CustomAsyncIterable:
            async def __aiter__(self) -> None:
                for i in range(5):
                    yield str(i + 1)

        response = StreamingResponse(CustomAsyncIterable(), media_type="text/plain")  # type: ignore
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.text == "12345"


def test_sync_streaming_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        def numbers(minimum: int, maximum: int) -> str:
            for i in range(minimum, maximum + 1):
                yield str(i)
                if i != maximum:
                    yield ", "

        generator = numbers(1, 5)
        response = StreamingResponse(generator, media_type="text/plain")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.text == "1, 2, 3, 4, 5"


def test_response_headers() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        headers = {"x-header-1": "123", "x-header-2": "456"}
        response = Response("hello, world", media_type="text/plain", headers=headers)
        response.headers["x-header-2"] = "789"
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.headers["x-header-1"] == "123"
    assert response.headers["x-header-2"] == "789"


def test_response_phrase() -> None:
    app = Response(content=None, status_code=204)
    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.reason_phrase == "No Content"

    app = Response(b"", status_code=123)
    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.reason_phrase == ""


def test_file_response(tmpdir: Path) -> None:
    path = tmpdir / "xyz"
    content = b"<file content>" * 1000
    Path(path).write_bytes(content)

    filled_by_bg_task = ""

    async def numbers(minimum, maximum) -> None:
        for i in range(minimum, maximum + 1):
            yield str(i)
            if i != maximum:
                yield ", "
            await anyio.sleep(0)

    async def numbers_for_cleanup(start=1, stop=5) -> None:
        nonlocal filled_by_bg_task
        async for thing in numbers(start, stop):
            filled_by_bg_task = filled_by_bg_task + thing

    cleanup_task = BackgroundTask(numbers_for_cleanup, start=6, stop=9)

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = FileResponse(path=path, filename="example.png", background=cleanup_task)
        await response(scope, receive, send)

    assert filled_by_bg_task == ""
    client = TestClient(app)  # type: ignore
    response = client.get("/")
    expected_disposition = 'attachment; filename="example.png"'
    assert response.status_code == HTTP_200_OK
    assert response.content == content
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"] == expected_disposition
    assert "content-length" in response.headers
    assert "last-modified" in response.headers
    assert "etag" in response.headers
    assert filled_by_bg_task == "6, 7, 8, 9"


def test_file_response_with_directory_raises_error(tmpdir: Path) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        FileResponse(path=tmpdir, filename="example.png")


def test_file_response_with_missing_file_raises_error(tmpdir: Path) -> None:
    path = tmpdir / "404.txt"
    with pytest.raises(ImproperlyConfiguredException):
        FileResponse(path=path, filename="404.txt")


def test_file_response_with_chinese_filename(tmpdir: Path) -> None:
    content = b"file content"
    filename = "你好.txt"
    path = tmpdir / filename
    Path(path).write_bytes(content)
    app = FileResponse(path=path, filename=filename)
    client = TestClient(app)  # type: ignore
    response = client.get("/")
    expected_disposition = "attachment; filename*=utf-8''%e4%bd%a0%e5%a5%bd.txt"
    assert response.status_code == HTTP_200_OK
    assert response.content == content
    assert response.headers["content-disposition"] == expected_disposition


def test_file_response_with_inline_disposition(tmpdir: Path) -> None:
    content = b"file content"
    filename = "hello.txt"
    path = tmpdir / filename
    Path(path).write_bytes(content)
    app = FileResponse(path=path, filename=filename, content_disposition_type="inline")
    client = TestClient(app)  # type: ignore
    response = client.get("/")
    expected_disposition = 'inline; filename="hello.txt"'
    assert response.status_code == HTTP_200_OK
    assert response.content == content
    assert response.headers["content-disposition"] == expected_disposition


def test_set_cookie() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = Response("Hello, world!", media_type="text/plain")
        response.set_cookie(
            "mycookie",
            "myvalue",
            max_age=10,
            expires=10,
            path="/",
            domain="localhost",
            secure=True,
            httponly=True,
            samesite="none",
        )
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.text == "Hello, world!"


def test_delete_cookie() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        response = Response("Hello, world!", media_type="text/plain")
        if request.cookies.get("mycookie"):
            response.delete_cookie("mycookie")
        else:
            response.set_cookie("mycookie", "myvalue")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.cookies["mycookie"]
    response = client.get("/")
    assert not response.cookies.get("mycookie")


def test_populate_headers() -> None:
    app = Response(content="hi", headers={}, media_type="text/html")
    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.text == "hi"
    assert response.headers["content-length"] == "2"
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_head_method() -> None:
    app = Response("hello, world", media_type="text/plain")
    client = TestClient(app)  # type: ignore
    response = client.head("/")
    assert response.text == ""


@pytest.mark.parametrize(
    "media_type, expected, should_have_content_length",
    ((MediaType.TEXT, b"", False), (MediaType.HTML, b"", False), (MediaType.JSON, b"null", True)),
)
def test_empty_response(media_type: MediaType, expected: bytes, should_have_content_length: bool) -> None:
    app = Response(content=None, media_type=media_type)
    client: TestClient = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.content == expected
    if should_have_content_length:
        assert "content-length" in response.headers
    else:
        assert "content-length" not in response.headers


def test_empty_204_response() -> None:
    app = Response(content=None, status_code=204)
    client: TestClient = TestClient(app)  # type: ignore
    response = client.get("/")
    assert "content-length" not in response.headers


def test_non_empty_response() -> None:
    app = Response(content="hi")
    client: TestClient = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.headers["content-length"] == "2"


def test_file_response_known_size(tmpdir: Path) -> None:
    path = tmpdir / "xyz"
    content = b"<file content>" * 1000
    Path(path).write_bytes(content)
    app = FileResponse(path=path, filename="example.png")
    client: TestClient = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.headers["content-length"] == str(len(content))


def test_streaming_response_unknown_size() -> None:
    app = StreamingResponse(content=iter(["hello", "world"]))
    client: TestClient = TestClient(app)  # type: ignore
    response = client.get("/")
    assert "content-length" not in response.headers


def test_streaming_response_known_size() -> None:
    app = StreamingResponse(content=iter(["hello", "world"]), headers={"content-length": "10"})
    client: TestClient = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.headers["content-length"] == "10"


async def test_streaming_response_stops_if_receiving_http_disconnect(anyio_backend: str) -> None:
    streamed = 0

    disconnected = anyio.Event()

    async def receive_disconnect() -> None:
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        nonlocal streamed
        if message["type"] == "http.response.body":
            streamed += len(message.get("body", b""))
            # Simulate disconnection after download has started
            if streamed >= 16:
                await disconnected.set()

    async def stream_indefinitely() -> None:
        while True:
            # Need a sleep for the event loop to switch to another task
            await anyio.sleep(0)
            yield b"chunk "

    response = StreamingResponse(content=stream_indefinitely())

    with anyio.move_on_after(1) as cancel_scope:
        await response({}, receive_disconnect, send)
    assert not cancel_scope.cancel_called, "Content streaming should stop itself."
