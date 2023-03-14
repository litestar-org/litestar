from typing import Any, Dict

from starlite import Request, Starlite, get
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.memory import MemoryStore

from starlite.testing import TestClient

session_config = ServerSideSessionConfig(store=MemoryStore())


@get(path="/test")
def get_session_data(request: Request) -> Dict[str, Any]:
    return request.session


app = Starlite(route_handlers=[get_session_data], middleware=[session_config.middleware])

with TestClient(app=app, session_config=session_config) as client:
    client.set_session_data({"foo": "bar"})
    assert client.get("/test").json() == {"foo": "bar"}
