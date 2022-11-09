from typing import TYPE_CHECKING

from starlite.datastructures import MutableScopeHeaders
from starlite.enums import ScopeType
from starlite.middleware.base import AbstractMiddleware

if TYPE_CHECKING:
    from starlite.config.cors import CORSConfig
    from starlite.types import ASGIApp, Receive, Scope, Send


class CORSMiddleware(AbstractMiddleware):
    def __init__(self, app: "ASGIApp", config: "CORSConfig"):
        super().__init__(
            app=app, exclude=config.exclude, exclude_opt_key=config.exclude_opt_key, scopes={ScopeType.HTTP}
        )
        self.config = config

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        headers = MutableScopeHeaders(scope=scope)

        origin = headers.get("origin")

        if not origin:
            await self.app(scope, receive, send)
            return
