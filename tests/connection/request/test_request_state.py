from typing import TYPE_CHECKING, Dict

from starlite import Request, get
from starlite.middleware import MiddlewareProtocol
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Receive, Scope, Send


class BeforeRequestMiddleWare(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp") -> None:
        self.app = app

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        scope["state"]["main"] = 1
        await self.app(scope, receive, send)


def before_request(request: Request) -> None:
    assert request.state.main == 1
    request.state.main = 2


def test_state() -> None:
    @get(path="/")
    async def get_state(request: Request) -> Dict[str, str]:
        return {"state": request.state.main}

    with create_test_client(
        route_handlers=[get_state], middleware=[BeforeRequestMiddleWare], before_request=before_request
    ) as client:
        response = client.get("/")
        assert response.json() == {"state": 2}
