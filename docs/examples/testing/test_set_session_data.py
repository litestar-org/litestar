from typing import Any

from litestar import Litestar, Request, get
from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.server_side import ServerSideSessionBackend, ServerSideSessionConfig
from litestar.testing import TestClient

session_config = ServerSideSessionConfig()


@get(path="/test", sync_to_thread=False)
def get_session_data(request: Request) -> dict[str, Any]:
    return request.session


app = Litestar(
    route_handlers=[get_session_data],
    middleware=[SessionMiddleware(ServerSideSessionBackend(session_config))],
    debug=True,
)


def test_get_session_data() -> None:
    with TestClient(app=app, session_config=session_config) as client:
        client.set_session_data({"foo": "bar"})
        assert client.get("/test").json() == {"foo": "bar"}
