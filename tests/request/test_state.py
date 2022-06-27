from typing import Dict

from starlette.types import ASGIApp, Receive, Scope, Send

from starlite import MiddlewareProtocol, Request, get
from starlite.testing import create_test_client


class BeforeRequestMiddleWare(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["state"]["main"] = "Success!"
        await self.app(scope, receive, send)


def before_request(request: Request) -> None:
    assert request.state.main == "Success!"
    request.state.main = "Success! x2"


def test_state() -> None:
    @get(path="/")
    async def get_state(request: Request) -> Dict[str, str]:
        return {"state": request.state.main}

    with create_test_client(
        route_handlers=[get_state], middleware=[BeforeRequestMiddleWare], before_request=before_request
    ) as client:
        response = client.get("/")
        assert response.json() == {"state": "Success! x2"}
