from litestar import Litestar, Request, post
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.testing import TestClient

session_config = ServerSideSessionConfig()


@post(path="/test", sync_to_thread=False)
def set_session_data(request: Request) -> None:
    request.session["foo"] = "bar"


app = Litestar(route_handlers=[set_session_data], middleware=[session_config.middleware], debug=True)

with TestClient(app=app, session_config=session_config) as client:
    client.post("/test").json()
    assert client.get_session_data() == {"foo": "bar"}
