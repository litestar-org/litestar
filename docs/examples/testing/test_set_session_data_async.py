from typing import Any, Dict

from starlite import Request, Starlite, get
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.memory import MemoryStore
from starlite.testing import AsyncTestClient

session_config = ServerSideSessionConfig(store=MemoryStore())


@get(path="/test")
def get_session_data(request: Request) -> Dict[str, Any]:
    return request.session


app = Starlite(route_handlers=[get_session_data], middleware=[session_config.middleware])


async def test_get_session_data() -> None:
    async with AsyncTestClient(app=app, session_config=session_config) as client:
        await client.set_session_data({"foo": "bar"})
        res = await client.get("/test")
        assert res.json() == {"foo": "bar"}
