from litestar.middleware import ASGIMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send


class MyMiddleware(ASGIMiddleware):
    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        # do stuff
        await next_app(scope, receive, send)
