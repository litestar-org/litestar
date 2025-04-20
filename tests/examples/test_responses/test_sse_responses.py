from docs.examples.responses.sse_responses import app
from httpx_sse import aconnect_sse

from litestar.testing import AsyncTestClient


async def test_sse_responses_example() -> None:
    async with AsyncTestClient(app=app) as client:
        async with aconnect_sse(client, "GET", f"{client.base_url}/count") as event_source:
            events = [sse async for sse in event_source.aiter_sse()]
            assert len(events) == 50


async def test_sse_responses_example_with_ping_events() -> None:
    async with AsyncTestClient(app=app) as client:
        async with aconnect_sse(client, "GET", f"{client.base_url}/with_ping") as event_source:
            events = [sse async for sse in event_source.aiter_sse()]
            for i in range(9):
                assert events[i].event == " ping"
            assert events[10].event == "message"
            assert events[10].data == "content"
