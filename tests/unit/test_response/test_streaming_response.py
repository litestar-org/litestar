# pyright: reportUnnecessaryTypeIgnoreComment=false

"""A large part of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are meant to ensure our compatibility with
their API.
"""

from collections.abc import AsyncIterator, Iterator
from itertools import cycle
from typing import TYPE_CHECKING

import anyio

from litestar import asgi, get
from litestar.background_tasks import BackgroundTask
from litestar.response.streaming import ASGIStreamingResponse
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.types import Message, Receive, Scope, Send


def test_streaming_response_unknown_size() -> None:
    @get("/")
    async def handler() -> ASGIStreamingResponse:
        return ASGIStreamingResponse(iterator=iter(["hello", "world"]))

    with create_test_client(handler) as client:
        response = client.get("/")

    assert "content-length" not in response.headers


def test_streaming_response_known_size() -> None:
    @get("/")
    async def handler() -> ASGIStreamingResponse:
        return ASGIStreamingResponse(iterator=iter(["hello", "world"]), headers={"content-length": "10"})

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.headers["content-length"] == "10"


async def test_streaming_response_stops_if_receiving_http_disconnect_with_async_iterator(anyio_backend: str) -> None:
    streamed = 0

    disconnected = anyio.Event()

    async def receive_disconnect() -> dict:
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message: "Message") -> None:
        nonlocal streamed
        if message["type"] == "http.response.body":
            streamed += len(message.get("body", b""))
            # Simulate disconnection after download has started
            if streamed >= 16:
                disconnected.set()

    async def stream_indefinitely() -> AsyncIterator[bytes]:
        while True:
            # Need a sleep for the event loop to switch to another task
            await anyio.sleep(0)
            yield b"chunk "

    response = ASGIStreamingResponse(iterator=stream_indefinitely())

    with anyio.move_on_after(1) as cancel_scope:
        await response({}, receive_disconnect, send)  # type: ignore[arg-type]
    assert not cancel_scope.cancel_called, "Content streaming should stop itself."


async def test_streaming_response_stops_if_receiving_http_disconnect_with_sync_iterator(anyio_backend: str) -> None:
    streamed = 0

    disconnected = anyio.Event()

    async def receive_disconnect() -> dict:
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message: "Message") -> None:
        nonlocal streamed
        if message["type"] == "http.response.body":
            streamed += len(message.get("body", b""))
            # Simulate disconnection after download has started
            if streamed >= 16:
                disconnected.set()

    response = ASGIStreamingResponse(iterator=cycle(["1", "2", "3"]))

    with anyio.move_on_after(1) as cancel_scope:
        await response({}, receive_disconnect, send)  # type: ignore[arg-type]
    assert not cancel_scope.cancel_called, "Content streaming should stop itself."


def test_streaming_response() -> None:
    filled_by_bg_task = ""

    @asgi("/")
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        async def numbers(minimum: int, maximum: int) -> AsyncIterator[str]:
            for i in range(minimum, maximum + 1):
                yield str(i)
                if i != maximum:
                    yield ", "
                await anyio.sleep(0)

        async def numbers_for_cleanup(start: int = 1, stop: int = 5) -> None:
            nonlocal filled_by_bg_task
            async for thing in numbers(start, stop):
                filled_by_bg_task += thing

        cleanup_task = BackgroundTask(numbers_for_cleanup, start=6, stop=9)
        generator = numbers(1, 5)
        response = ASGIStreamingResponse(iterator=generator, media_type="text/plain", background=cleanup_task)
        await response(scope, receive, send)

    assert not filled_by_bg_task
    with create_test_client([handler]) as client:
        response = client.get("/")
        assert response.text == "1, 2, 3, 4, 5"
        assert filled_by_bg_task == "6, 7, 8, 9"  # type: ignore[comparison-overlap]


def test_streaming_response_custom_iterator() -> None:
    @asgi("/")
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        class CustomAsyncIterator:
            def __init__(self) -> None:
                self._called = 0

            def __aiter__(self) -> "CustomAsyncIterator":
                return self

            async def __anext__(self) -> str:
                if self._called == 5:
                    raise StopAsyncIteration()
                self._called += 1
                return str(self._called)

        response = ASGIStreamingResponse(iterator=CustomAsyncIterator(), media_type="text/plain")
        await response(scope, receive, send)

    with create_test_client([handler]) as client:
        response = client.get("/")
        assert response.text == "12345"


def test_streaming_response_custom_iterable() -> None:
    @asgi("/")
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        class CustomAsyncIterable:
            async def __aiter__(self) -> AsyncIterator[str]:
                for i in range(5):
                    yield str(i + 1)

        response = ASGIStreamingResponse(iterator=CustomAsyncIterable(), media_type="text/plain")
        await response(scope, receive, send)

    with create_test_client([handler]) as client:
        response = client.get("/")
        assert response.text == "12345"


def test_sync_streaming_response() -> None:
    @asgi("/")
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        def numbers(minimum: int, maximum: int) -> Iterator[str]:
            for i in range(minimum, maximum + 1):
                yield str(i)
                if i != maximum:
                    yield ", "

        generator = numbers(1, 5)
        response = ASGIStreamingResponse(iterator=generator, media_type="text/plain")
        await response(scope, receive, send)

    with create_test_client([handler]) as client:
        response = client.get("/")
        assert response.text == "1, 2, 3, 4, 5"

def test_asgi_streaming_response_headers_tuple_iterable() -> None:
    """Test that ASGIStreamingResponse accepts headers as iterable of tuples."""
    from litestar.response.streaming import ASGIStreamingResponse

    # Test with iterable of tuples (allows repeated headers)
    headers = [
        ("set-cookie", "cookie1=value1; Path=/"),
        ("set-cookie", "cookie2=value2; Path=/"),
        ("x-custom", "value"),
    ]

    response = ASGIStreamingResponse(
        iterator=iter(["hello"]),
        headers=headers,
    )


from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

import pytest

from litestar import get
from litestar.response.streaming import ASGIStreamingResponse, Stream
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.types import Message, Receive, Scope, Send


def test_asgi_streaming_response_headers_tuple_iterable() -> None:
    """Test that ASGIStreamingResponse accepts headers as iterable of tuples."""
    headers = [
        ("set-cookie", "cookie1=value1; Path=/"),
        ("set-cookie", "cookie2=value2; Path=/"),
        ("x-custom", "value"),
    ]

    response = ASGIStreamingResponse(
        iterator=iter(["hello"]),
        headers=headers,
    )

    # Check that headers are stored correctly in MutableScopeHeaders
    assert response.headers.get_list("set-cookie") == [
        "cookie1=value1; Path=/",
        "cookie2=value2; Path=/",
    ]
    assert response.headers.get("x-custom") == "value"


def test_asgi_streaming_response_headers_dict() -> None:
    """Test that ASGIStreamingResponse still accepts headers as dict."""
    headers = {
        "content-type": "text/plain",
        "x-custom": "value",
    }

    response = ASGIStreamingResponse(
        iterator=iter(["hello"]),
        headers=headers,
    )

    assert response.headers.get("content-type") == "text/plain"
    assert response.headers.get("x-custom") == "value"


def test_asgi_streaming_response_headers_none() -> None:
    """Test that ASGIStreamingResponse handles headers=None by creating empty headers."""
    response = ASGIStreamingResponse(
        iterator=iter(["hello"]),
        headers=None,
    )

    # Empty MutableScopeHeaders, not None
    assert response.headers is not None
    assert len(response.headers) == 0


async def test_to_asgi_response_headers_tuple_iterable() -> None:
    """Test Stream.to_asgi_response with headers as iterable of tuples."""
    from litestar.types import Message, Receive, Scope, Send

    async def stream_content() -> AsyncIterator[str]:
        yield "hello"
        yield "world"

    @get("/")
    async def handler() -> Stream:
        return Stream(
            content=stream_content(),
            headers=[
                ("set-cookie", "cookie1=value1"),
                ("set-cookie", "cookie2=value2"),
            ],
        )

    with create_test_client([handler]) as client:
        response = client.get("/")
        assert response.text == "helloworld"
        # Check both set-cookie headers are present
        assert response.headers.get_list("set-cookie") == [
            "cookie1=value1",
            "cookie2=value2",
        ]


async def test_stream_to_asgi_response_headers_tuple_iterable() -> None:
    """Test Stream.to_asgi_response with headers as iterable of tuples."""
    from litestar.types import Message, Receive, Scope, Send

    async def stream_content() -> AsyncIterator[str]:
        yield "test"

    stream = Stream(
        content=stream_content(),
        headers=[
            ("x-header-1", "value1"),
            ("x-header-2", "value2"),
        ],
    )

    messages: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request"}

    async def send(message: Message) -> None:
        messages.append(message)

    from litestar.connection import Request
    from litestar.testing import RequestFactory

    request = RequestFactory().get("/")
    asgi_response = await stream.to_asgi_response(request=request)

    messages = []

    async def send(message: Message) -> None:
        messages.append(message)

    await asgi_response(request.scope, receive, send)

    # Check headers were sent correctly
    start_messages = [m for m in messages if m["type"] == "http.response.start"]
    assert len(start_messages) == 1
    start_message = start_messages[0]
    headers = start_message.get("headers", [])

    # Should contain both headers from tuple iterable
    header_names = [h[0].decode() for h in headers]
    assert "x-header-1" in header_names
    assert "x-header-2" in header_names


async def test_stream_to_asgi_response_merges_additional_headers() -> None:
    """Test that additional headers passed to to_asgi_response are merged with existing headers."""
    from litestar.types import Message, Receive, Scope, Send

    async def stream_content() -> AsyncIterator[str]:
        yield "test"

    stream = Stream(
        content=stream_content(),
        headers={"x-original": "value1"},
    )

    messages: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request"}

    async def send(message: Message) -> None:
        messages.append(message)

    from litestar.connection import Request
    from litestar.testing import RequestFactory

    request = RequestFactory().get("/")
    asgi_response = await stream.to_asgi_response(
        request=request,
        headers=[("x-additional", "value2")],
    )

    messages = []

    async def send(message: Message) -> None:
        messages.append(message)

    await asgi_response(request.scope, receive, send)

    # Check headers were sent correctly - both original and additional
    start_messages = [m for m in messages if m["type"] == "http.response.start"]
    assert len(start_messages) == 1
    start_message = start_messages[0]
    headers = start_message.get("headers", [])

    header_dict = {h[0].decode(): h[1].decode() for h in headers}
    assert header_dict.get("x-original") == "value1"
    assert header_dict.get("x-additional") == "value2"
