from typing import TYPE_CHECKING, cast

from starlite.config import CompressionBackend, CompressionConfig
from starlite.types import MiddlewareProtocol
from starlite.utils import import_string

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


class CompressionMiddleware(MiddlewareProtocol):
    """Compression middleware for Starlite

    This is a class to store the configured compression backend for Starlite
    """

    def __init__(self, app: "ASGIApp", config: CompressionConfig) -> None:
        self._handler = _load_compression_middleware(app, config)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        return await self.handler(scope, receive, send)

    @property
    def handler(self) -> MiddlewareProtocol:
        """ASGI Handler

        Returns:
            MiddlewareProtocol: Returns the configured compression middleware class
        """
        return self._handler


def _load_compression_middleware(app: "ASGIApp", config: CompressionConfig) -> "MiddlewareProtocol":
    if config.backend == CompressionBackend.GZIP:
        handler = import_string("starlite.middleware.compression.gzip.GZipMiddleware")
    elif config.backend == CompressionBackend.BROTLI:
        handler = import_string("starlite.middleware.compression.brotli.BrotliMiddleware")
    else:
        raise ValueError("Unknown compression backend")
    return cast("MiddlewareProtocol", handler(app=app, **config.dict()))
