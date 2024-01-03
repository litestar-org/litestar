"""A large part of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are meant to ensure our compatibility with
their API.
"""
from itertools import cycle
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator, List

import anyio
import pytest
from httpx_sse import ServerSentEvent as HTTPXServerSentEvent
from httpx_sse import aconnect_sse

from litestar import get
from litestar.background_tasks import BackgroundTask
from litestar.response import ServerSentEvent
from litestar.response.sse import ServerSentEventMessage
from litestar.response.streaming import ASGIStreamingResponse
from litestar.testing import TestClient, create_async_test_client

if TYPE_CHECKING:
    from litestar.types import Message, Receive, Scope, Send


def test_streaming_response_unknown_size() -> None:
    app = ASGIStreamingResponse(iterator=iter(["hello", "world"]))
    client = TestClient(app)
    response = client.get("/")
    assert "content-length" not in response.headers


def test_streaming_response_known_size() -> None:
    app = ASGIStreamingResponse(iterator=iter(["hello", "world"]), headers={"content-length": "10"})
    client = TestClient(app)
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
        await response({}, receive_disconnect, send)  # type: ignore
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
        await response({}, receive_disconnect, send)  # type: ignore
    assert not cancel_scope.cancel_called, "Content streaming should stop itself."


def test_streaming_response() -> None:
    filled_by_bg_task = ""

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
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
    client = TestClient(app)
    response = client.get("/")
    assert response.text == "1, 2, 3, 4, 5"
    assert filled_by_bg_task == "6, 7, 8, 9"


def test_streaming_response_custom_iterator() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
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

    client = TestClient(app)
    response = client.get("/")
    assert response.text == "12345"


def test_streaming_response_custom_iterable() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        class CustomAsyncIterable:
            async def __aiter__(self) -> AsyncIterator[str]:
                for i in range(5):
                    yield str(i + 1)

        response = ASGIStreamingResponse(iterator=CustomAsyncIterable(), media_type="text/plain")
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/")
    assert response.text == "12345"


def test_sync_streaming_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        def numbers(minimum: int, maximum: int) -> Iterator[str]:
            for i in range(minimum, maximum + 1):
                yield str(i)
                if i != maximum:
                    yield ", "

        generator = numbers(1, 5)
        response = ASGIStreamingResponse(iterator=generator, media_type="text/plain")
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/")
    assert response.text == "1, 2, 3, 4, 5"


async def test_sse_steaming_response() -> None:
    @get(
        path="/test",
    )
    def handler() -> ServerSentEvent:
        def numbers(minimum: int, maximum: int) -> Iterator[str]:
            for i in range(minimum, maximum + 1):
                yield str(i)

        generator = numbers(1, 5)

        return ServerSentEvent(content=generator, event_id="123", event_type="special", retry_duration=1000)

    async with create_async_test_client(handler) as client:
        async with aconnect_sse(client, "GET", f"{client.base_url}/test") as event_source:
            events = [sse async for sse in event_source.aiter_sse()]
            assert len(events) == 5
            for idx, sse in enumerate(events, start=1):
                assert sse.event == "special"
                assert sse.data == str(idx)
                assert sse.id == "123"
                assert sse.retry == 1000


def test_asgi_response_encoded_headers() -> None:
    response = ASGIStreamingResponse(encoded_headers=[(b"foo", b"bar")], iterator="")
    assert response.encode_headers() == [(b"foo", b"bar"), (b"content-type", b"application/json")]


@pytest.mark.parametrize(
    "input,expected_events",
    [
        ("string", [HTTPXServerSentEvent(event="special", data=str(i), id="123", retry=1000) for i in range(1, 6)]),
        ("integer", [HTTPXServerSentEvent(event="special", data=str(i), id="123", retry=1000) for i in range(1, 6)]),
        ("dict1", [HTTPXServerSentEvent(event="special", data=str(i), id="123", retry=1000) for i in range(1, 6)]),
        (
            "dict2",
            [
                HTTPXServerSentEvent(
                    event=e, data=str(i) if e == "event1" else str(2 * i), id="123", retry=1000 if e == "event1" else 10
                )
                for i in range(1, 6)
                for e in ["event1", "event2"]
            ],
        ),
        ("obj", [HTTPXServerSentEvent(event="special", data=str(i), id="123", retry=1000) for i in range(1, 6)]),
    ],
)
async def test_various_sse_inputs(input: str, expected_events: List[HTTPXServerSentEvent]) -> None:
    @get("/testme")
    async def handler() -> ServerSentEvent:
        async def numbers(minimum: int, maximum: int) -> AsyncIterator[Any]:
            for i in range(minimum, maximum + 1):
                await anyio.sleep(0.1)
                if input == "integer":
                    yield i
                elif input == "string":
                    yield str(i)
                elif input == "dict1":
                    yield {"data": i, "event": "special", "retry": 1000}
                elif input == "dict2":
                    yield {"data": i, "event": "event1", "retry": 1000}
                    yield {"data": 2 * i, "event": "event2", "retry": 10}
                elif input == "obj":
                    yield ServerSentEventMessage(data=i, event="special", retry=1000)

        generator = numbers(1, 5)
        return ServerSentEvent(generator, event_type="special", event_id="123", retry_duration=1000)

    async with create_async_test_client(handler) as client:
        async with aconnect_sse(client, "GET", f"{client.base_url}/testme") as event_source:
            events = [sse async for sse in event_source.aiter_sse()]
            assert len(events) == len(expected_events)
            for i in range(len(expected_events)):
                assert events[i].event == expected_events[i].event
                assert events[i].data == expected_events[i].data
                assert events[i].id == expected_events[i].id
                assert events[i].retry == expected_events[i].retry
