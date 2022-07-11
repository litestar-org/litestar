import io
from enum import Enum
from typing import TYPE_CHECKING, Union

from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.gzip import GZipResponder, unattached_send

from starlite.config import BrotliMode
from starlite.enums import ScopeType
from starlite.exceptions import MissingDependencyException

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


try:
    import brotli
except ImportError as e:
    raise MissingDependencyException("brotli is not installed") from e


class ContentEncoding(str, Enum):
    GZIP = "gzip"
    BROTLI = "br"


class BrotliMiddleware:
    """Brotli middleware for Starlite

    Compresses responses using Brotli and optionally fall back to Gzip.
    """

    def __init__(
        self,
        app: "ASGIApp",
        minimum_size: int = 400,
        brotli_quality: int = 4,
        brotli_mode: BrotliMode = BrotliMode.TEXT,
        brotli_lgwin: int = 22,
        brotli_lgblock: int = 0,
        brotli_gzip_fallback: bool = True,
    ) -> None:
        self.app = app
        self.quality = brotli_quality
        self.mode = _brotli_mode_lookup(brotli_mode)
        self.minimum_size = minimum_size
        self.lgwin = brotli_lgwin
        self.lgblock = brotli_lgblock
        self.gzip_fallback = brotli_gzip_fallback

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] == ScopeType.HTTP:
            headers = Headers(scope=scope)
            if ContentEncoding.BROTLI in headers.get("Accept-Encoding", ""):
                brotli_responser = BrotliResponder(
                    app=self.app,
                    minimum_size=self.minimum_size,
                    quality=self.quality,
                    mode=self.mode,
                    lgwin=self.lgwin,
                    lgblock=self.lgblock,
                )
                await brotli_responser(scope, receive, send)
                return
            if self.gzip_fallback and ContentEncoding.GZIP in headers.get("Accept-Encoding", ""):
                gzip_responder = GZipResponder(self.app, self.minimum_size)
                await gzip_responder(scope, receive, send)
                return
        await self.app(scope, receive, send)


class BrotliResponder:
    """Brotli Responder

    Formats a response with Brotli compression.
    """

    def __init__(
        self,
        app: "ASGIApp",
        minimum_size: int,
        quality: int,
        mode: int,
        lgwin: int,
        lgblock: int,
    ) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.send: "Send" = unattached_send
        self.initial_message: "Message" = {}
        self.started = False
        self.br_buffer = io.BytesIO()
        self.quality = quality
        self.mode = mode
        self.lgwin = lgwin
        self.lgblock = lgblock
        self.br_file = brotli.Compressor(quality=self.quality, mode=self.mode, lgwin=self.lgwin, lgblock=self.lgblock)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        self.send = send
        await self.app(scope, receive, self.send_with_brotli)

    async def send_with_brotli(self, message: "Message") -> None:
        """Handles and compresses the HTTP Message with brotli

        Args:
            message (Message): ASGI HTTP Message
        """
        message_type = message["type"]
        if message_type == "http.response.start":
            # Don't send the initial message until we've determined how to
            # modify the outgoing headers correctly.
            self.initial_message = message
        elif message_type == "http.response.body" and not self.started:
            self.started = True
            body = message.get("body", b"")
            more_body = message.get("more_body", False)
            if len(body) < self.minimum_size and not more_body:
                # Don't apply Brotli to small outgoing responses.
                await self.send(self.initial_message)
                await self.send(message)
            elif not more_body:
                # Standard Brotli response.
                body = self.br_file.process(body) + self.br_file.finish()
                headers = MutableHeaders(raw=self.initial_message["headers"])
                headers["Content-Encoding"] = ContentEncoding.BROTLI
                headers["Content-Length"] = str(len(body))
                headers.add_vary_header("Accept-Encoding")
                message["body"] = body

                await self.send(self.initial_message)
                await self.send(message)
            else:
                # Initial body in streaming Brotli response.
                headers = MutableHeaders(raw=self.initial_message["headers"])
                headers["Content-Encoding"] = ContentEncoding.BROTLI
                headers.add_vary_header("Accept-Encoding")
                del headers["Content-Length"]
                self.br_buffer.write(self.br_file.process(body) + self.br_file.flush())
                message["body"] = self.br_buffer.getvalue()
                self.br_buffer.seek(0)
                self.br_buffer.truncate()
                await self.send(self.initial_message)
                await self.send(message)

        elif message_type == "http.response.body":
            # Remaining body in streaming Brotli response.
            body = message.get("body", b"")
            more_body = message.get("more_body", False)
            self.br_buffer.write(self.br_file.process(body) + self.br_file.flush())
            if not more_body:
                self.br_buffer.write(self.br_file.finish())

            message["body"] = self.br_buffer.getvalue()

            self.br_buffer.seek(0)
            self.br_buffer.truncate()
            if not more_body:
                self.br_buffer.close()
            await self.send(message)


def _brotli_mode_lookup(mode: Union[BrotliMode, str]) -> int:
    if isinstance(mode, str):
        # convert to enum
        mode = getattr(BrotliMode, mode.upper())
    if mode == BrotliMode.TEXT:
        return int(brotli.MODE_TEXT)
    if mode == BrotliMode.FONT:
        return int(brotli.MODE_FONT)
    return int(brotli.MODE_GENERIC)
