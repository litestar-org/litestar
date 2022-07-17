from typing import TYPE_CHECKING, cast

from starlite.config import InstrumentationBackend, InstrumentationConfig
from starlite.types import MiddlewareProtocol
from starlite.utils import import_string

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


class InstrumentationMiddleware(MiddlewareProtocol):
    """Instrumentation middleware for Starlite

    This is a class to store the configured instrumentation backend for Starlite
    """

    def __init__(self, app: "ASGIApp", config: InstrumentationConfig) -> None:
        self._handler = _load_instrumentation_middleware(app, config)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        return await self.handler(scope, receive, send)

    @property
    def handler(self) -> MiddlewareProtocol:
        """ASGI Handler

        Returns:
            MiddlewareProtocol: Returns the configured intrumentation middleware class
        """
        return self._handler


def _load_instrumentation_middleware(app: "ASGIApp", config: InstrumentationConfig) -> MiddlewareProtocol:
    if config.backend == InstrumentationBackend.OPENTELEMETRY:
        handler = import_string("starlite.middleware.instrumentation.opentelemetry.OpenTelemetryMiddleware")
    else:
        raise ValueError("Unknown compression backend")
    return cast(MiddlewareProtocol, handler(app=app, **config.dict()))
