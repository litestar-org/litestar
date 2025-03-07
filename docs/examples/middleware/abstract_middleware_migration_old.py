import anyio

from litestar import Litestar
from litestar.middleware import AbstractMiddleware, DefineMiddleware
from litestar.types import ASGIApp, Receive, Scope, Scopes, Send


class TimeoutMiddleware(AbstractMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        timeout: float,
        exclude: str | list[str] | None = None,
        exclude_opt_key: str | None = None,
        scopes: Scopes | None = None,
    ):
        self.timeout = timeout
        super().__init__(app=app, exclude=exclude, exclude_opt_key=exclude_opt_key, scopes=scopes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        with anyio.move_on_after(self.timeout):
            await self.app(scope, receive, send)


app = Litestar(
    middleware=[
        DefineMiddleware(
            TimeoutMiddleware,
            timeout=5,
        )
    ]
)
