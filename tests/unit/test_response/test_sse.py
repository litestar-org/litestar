from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

import anyio
import pytest
from httpx_sse import ServerSentEvent as HTTPXServerSentEvent
from httpx_sse import aconnect_sse

from litestar import get
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response import ServerSentEvent
from litestar.response.sse import ASGIStreamingSSEResponse, ServerSentEventMessage
from litestar.testing import create_async_test_client
from litestar.types import SSEData

if TYPE_CHECKING:
    from litestar.types.asgi_types import HTTPDisconnectEvent, Message


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


@pytest.mark.parametrize(
    "input,expected_events",
    [
        ("string", [HTTPXServerSentEvent(event="special", data=str(i), id="123", retry=1000) for i in range(1, 6)]),
        ("bytes", [HTTPXServerSentEvent(event="special", data=str(i), id="123", retry=1000) for i in range(1, 6)]),
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
        ("empty", [HTTPXServerSentEvent(event="something-empty", id="123", retry=1000) for i in range(1, 6)]),
        ("comment", [HTTPXServerSentEvent(event="something-with-comment", id="123", retry=1000) for i in range(1, 6)]),
    ],
)
async def test_various_sse_inputs(input: str, expected_events: list[HTTPXServerSentEvent]) -> None:
    @get("/testme")
    async def handler() -> ServerSentEvent:
        async def numbers() -> AsyncIterator[SSEData]:
            for i in range(1, 6):
                await anyio.sleep(0.001)
                if input == "integer":
                    yield i
                elif input == "string":
                    yield str(i)
                elif input == "bytes":
                    yield str(i).encode("utf-8")
                elif input == "dict1":
                    yield {"data": i, "event": "special", "retry": 1000}
                elif input == "dict2":
                    yield {"data": i, "event": "event1", "retry": 1000}
                    yield {"data": 2 * i, "event": "event2", "retry": 10}
                elif input == "obj":
                    yield ServerSentEventMessage(data=i, event="special", retry=1000)
                elif input == "empty":
                    yield ServerSentEventMessage(event="something-empty", retry=1000)
                elif input == "comment":
                    yield ServerSentEventMessage(event="something-with-comment", retry=1000, comment="some comment")

        return ServerSentEvent(numbers(), event_type="special", event_id="123", retry_duration=1000)

    async with create_async_test_client(handler) as client:
        async with aconnect_sse(client, "GET", f"{client.base_url}/testme") as event_source:
            events = [sse async for sse in event_source.aiter_sse()]
            assert len(events) == len(expected_events)
            for i in range(len(expected_events)):
                assert events[i].event == expected_events[i].event
                assert events[i].data == expected_events[i].data
                assert events[i].id == expected_events[i].id
                assert events[i].retry == expected_events[i].retry


def test_invalid_content_type_raises() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ServerSentEvent(content=object())  # type: ignore[arg-type]


async def test_sse_without_ping_interval_works_unchanged() -> None:
    """Regression test: SSE without ping_interval behaves exactly as before."""

    @get("/test")
    async def handler() -> ServerSentEvent:
        async def gen() -> AsyncIterator[str]:
            for i in range(3):
                yield str(i)

        return ServerSentEvent(gen())

    async with create_async_test_client(handler) as client:
        async with aconnect_sse(client, "GET", f"{client.base_url}/test") as event_source:
            events = [sse async for sse in event_source.aiter_sse()]
            assert len(events) == 3
            for idx, sse in enumerate(events):
                assert sse.data == str(idx)


async def test_sse_ping_interval_sends_keepalive_comments() -> None:
    """SSE with ping_interval sends keepalive comments during idle periods."""

    @get("/test")
    async def handler() -> ServerSentEvent:
        async def gen() -> AsyncIterator[str]:
            await anyio.sleep(0.35)
            yield "done"

        return ServerSentEvent(gen(), ping_interval=0.1)

    async with create_async_test_client(handler) as client:
        response = await client.get("/test")
        body = response.content.decode()
        # Should contain at least one ping comment
        assert ": ping\r\n\r\n" in body
        # Should also contain the actual data
        assert "data: done" in body


async def test_sse_ping_uses_comments_not_events() -> None:
    """Pings must be SSE comments (start with ':'), not 'event: ping'."""

    @get("/test")
    async def handler() -> ServerSentEvent:
        async def gen() -> AsyncIterator[str]:
            await anyio.sleep(0.25)
            yield "data"

        return ServerSentEvent(gen(), ping_interval=0.1)

    async with create_async_test_client(handler) as client:
        response = await client.get("/test")
        body = response.content.decode()
        assert ": ping\r\n" in body
        assert "event: ping" not in body


async def test_sse_ping_stops_when_stream_ends() -> None:
    """Ping task should stop cleanly when the stream ends without task leaks."""

    @get("/test")
    async def handler() -> ServerSentEvent:
        async def gen() -> AsyncIterator[str]:
            yield "hello"
            yield "world"

        return ServerSentEvent(gen(), ping_interval=0.1)

    async with create_async_test_client(handler) as client:
        async with aconnect_sse(client, "GET", f"{client.base_url}/test") as event_source:
            events = [sse async for sse in event_source.aiter_sse()]
            assert len(events) == 2
            assert events[0].data == "hello"
            assert events[1].data == "world"


async def test_sse_concurrent_ping_and_data() -> None:
    """Rapid data emission with short ping interval should not corrupt the response."""

    @get("/test")
    async def handler() -> ServerSentEvent:
        async def gen() -> AsyncIterator[str]:
            for i in range(20):
                await anyio.sleep(0.02)
                yield str(i)

        return ServerSentEvent(gen(), ping_interval=0.05)

    async with create_async_test_client(handler) as client:
        response = await client.get("/test")
        body = response.content.decode()
        # All 20 data events should be present
        for i in range(20):
            assert f"data: {i}\r\n" in body


async def test_sse_ping_with_str_chunks() -> None:
    """ASGIStreamingSSEResponse handles str chunks correctly when ping is enabled."""

    async def str_iterator() -> AsyncIterator[str]:
        yield "hello"
        yield "world"

    response = ASGIStreamingSSEResponse(
        iterator=str_iterator(),
        ping_interval=0.1,
        media_type="text/event-stream",
        status_code=200,
    )

    received: list[bytes] = []

    async def mock_send(message: "Message") -> None:
        if message.get("type") == "http.response.body":
            body = message.get("body", b"")
            received.append(body if isinstance(body, bytes) else b"")

    async def mock_receive() -> "HTTPDisconnectEvent":
        await anyio.sleep(10)
        return {"type": "http.disconnect"}

    await response.send_body(mock_send, mock_receive)

    body = b"".join(received).decode()
    assert "hello" in body
    assert "world" in body
