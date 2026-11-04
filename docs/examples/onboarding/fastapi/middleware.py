import time

from litestar import Litestar, get
from litestar.datastructures import MutableScopeHeaders
from litestar.middleware import ASGIMiddleware
from litestar.types import ASGIApp, Message, Receive, Scope, Send


class ProcessTimeMiddleware(ASGIMiddleware):
    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        start_time = time.monotonic()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableScopeHeaders.from_message(message=message)
                headers["x-process-time"] = f"{time.monotonic() - start_time:.4f}"
            await send(message)

        await next_app(scope, receive, send_wrapper)


@get("/")
async def index() -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(route_handlers=[index], middleware=[ProcessTimeMiddleware()])
