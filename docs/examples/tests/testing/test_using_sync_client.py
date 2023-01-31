from typing import Any, Dict

from starlite import Request, Starlite, get, post
from starlite.middleware.session.memory_backend import MemoryBackendConfig
from starlite.testing import TestClient

session_config = MemoryBackendConfig()


@get(path="/test")
def get_session_data(request: Request) -> Dict[str, Any]:
    return request.session


@post(path="/test")
def set_session_data(request: Request) -> None:
    request.session["foo"] = "bar"


app = Starlite(route_handlers=[get_session_data, set_session_data], middleware=[session_config.middleware])

with TestClient(app=app, session_config=session_config) as client:
    client.set_session_data({"foo": "bar"})
    assert client.get("/test").json() == {"foo": "bar"}

with TestClient(app=app, session_config=session_config) as client:
    client.post("/test").json()
    assert client.get_session_data() == {"foo": "bar"}
