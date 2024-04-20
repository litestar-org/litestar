from typing import Protocol, Any
from litestar.types import ASGIApp, Scope, Receive, Send


class MiddlewareProtocol(Protocol):
    def __init__(self, app: ASGIApp, **kwargs: Any) -> None: ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...