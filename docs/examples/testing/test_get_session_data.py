from starlite import Request, Starlite, post
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.testing import TestClient

session_config = ServerSideSessionConfig()


@post(path="/test")
def set_session_data(request: Request) -> None:
    request.session["foo"] = "bar"


app = Starlite(route_handlers=[set_session_data], middleware=[session_config.middleware])

with TestClient(app=app, session_config=session_config) as client:
    client.post("/test").json()
    assert client.get_session_data() == {"foo": "bar"}
