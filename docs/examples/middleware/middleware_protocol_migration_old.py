from litestar.middleware import MiddlewareProtocol
from litestar.types import ASGIApp, Receive, Scope, Send


class MyMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # do stuff
        await self.app(scope, receive, send)
