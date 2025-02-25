import anyio

from litestar import Litestar
from litestar.middleware import ASGIMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send


class TimeoutMiddleware(ASGIMiddleware):
    def __init__(self, timeout: float):
        self.timeout = timeout

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        with anyio.move_on_after(self.timeout):
            await next_app(scope, receive, send)


app = Litestar(middleware=[TimeoutMiddleware(timeout=5)])
