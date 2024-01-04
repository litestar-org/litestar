from docs.examples.responses.sse_responses import app
from httpx_sse import aconnect_sse

from litestar.testing import AsyncTestClient


async def test_sse_responses_example() -> None:
    async with AsyncTestClient(app=app) as client:
        async with aconnect_sse(client, "GET", f"{client.base_url}/count") as event_source:
            events = [sse async for sse in event_source.aiter_sse()]
            assert len(events) == 10
        assert all(e.event == "message" for e in events)
        assert all(e.data == str(i) for i, e in enumerate(events, 1))
