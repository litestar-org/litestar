from typing import Any, Dict

from starlite import Request, Starlite, get, post
from starlite.middleware.session.memory_backend import MemoryBackendConfig
from starlite.testing import AsyncTestClient

session_config = MemoryBackendConfig()


@get(path="/test")
def get_session_data(request: Request) -> Dict[str, Any]:
    return request.session


@post(path="/test")
def set_session_data(request: Request) -> None:
    request.session["foo"] = "bar"


app = Starlite(route_handlers=[get_session_data, set_session_data], middleware=[session_config.middleware])


async def test_get_session_data() -> None:
    async with AsyncTestClient(app=app, session_config=session_config) as client:
        await client.set_session_data({"foo": "bar"})
        res = await client.get("/test")
        assert res.json() == {"foo": "bar"}


async def test_set_session_data() -> None:
    async with AsyncTestClient(app=app, session_config=session_config) as client:
        await client.post("/test")
        assert await client.get_session_data() == {"foo": "bar"}
