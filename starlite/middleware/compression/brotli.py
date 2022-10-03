import io
from enum import Enum
from typing import TYPE_CHECKING, Optional, cast

from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.gzip import GZipResponder
from typing_extensions import Literal

from starlite.enums import ScopeType
from starlite.exceptions import MissingDependencyException
from starlite.middleware.base import MiddlewareProtocol

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Message, Receive, Scope, Send
    from starlite.types.asgi_types import HTTPResponseStartEvent, HTTPScope

try:
    import brotli
except ImportError as e:
    raise MissingDependencyException("brotli is not installed") from e

BrotliMode = Literal["text", "generic", "font"]


class CompressionEncoding(str, Enum):
    """An Enum for supported compression encodings."""

    GZIP = "gzip"
    BROTLI = "br"


class BrotliMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: "ASGIApp",
        minimum_size: int = 400,
        brotli_quality: int = 4,
        brotli_mode: BrotliMode = "text",
        brotli_lgwin: int = 22,
        brotli_lgblock: int = 0,
        brotli_gzip_fallback: bool = True,
    ) -> None:
        """Brotli middleware for Starlite.

        Compresses responses using Brotli and optional fallback to Gzip.

        Args:
            app: The 'next' ASGI app to call.
            minimum_size: Minimum size for the response body to affect compression.
            brotli_quality: Controls the compression-speed vs compression-density tradeoffs.
                The higher the quality, the slower the compression. The range of this value is 0 to 11.
            brotli_mode: The encoder mode.
            brotli_lgwin: The base-2 logarithm of the sliding window size. The range of this value is 10 to 24.
            brotli_lgblock: The base-2 logarithm of the maximum input block size. The range of this value is 16 to 24.
                If set to 0, the value will be set based on quality.
            brotli_gzip_fallback: Allow falling back to GZIP.
        """
        self.app = app
        self.quality = brotli_quality
        self.mode = self._brotli_mode_to_int(brotli_mode)
        self.minimum_size = minimum_size
        self.lgwin = brotli_lgwin
        self.lgblock = brotli_lgblock
        self.gzip_fallback = brotli_gzip_fallback

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] == ScopeType.HTTP:
            headers = Headers(scope=scope)
            if CompressionEncoding.BROTLI in headers.get("Accept-Encoding", ""):
                brotli_responder = BrotliResponder(
                    app=self.app,
                    minimum_size=self.minimum_size,
                    quality=self.quality,
                    mode=self.mode,
                    lgwin=self.lgwin,
                    lgblock=self.lgblock,
                )
                await brotli_responder(scope, receive, send)
                return
            if self.gzip_fallback and CompressionEncoding.GZIP in headers.get("Accept-Encoding", ""):
                gzip_responder = GZipResponder(self.app, self.minimum_size)  # type: ignore[arg-type]
                await gzip_responder(scope, receive, send)  # type: ignore[arg-type]
                return
        await self.app(scope, receive, send)

    @staticmethod
    def _brotli_mode_to_int(brotli_mode: BrotliMode) -> int:
        """Select the correct brotli mode.

        Returns:
            An int correlating with the constants in the brotli package
        """
        if brotli_mode == "text":
            return int(brotli.MODE_TEXT)
        if brotli_mode == "font":
            return int(brotli.MODE_FONT)
        return int(brotli.MODE_GENERIC)


class BrotliResponder:
    def __init__(
        self,
        app: "ASGIApp",
        minimum_size: int,
        quality: int,
        mode: int,
        lgwin: int,
        lgblock: int,
    ) -> None:
        """Brotli Responder.

        Formats a response with Brotli compression.

        Args:
            app: The 'next' ASGI app to call.
            minimum_size: Minimum size for the response body to affect compression.
            quality: Controls the compression-speed vs compression-density tradeoffs.
                The higher the quality, the slower the compression. The range of this value is 0 to 11.
            mode: The encoder mode.
            lgwin: The base-2 logarithm of the sliding window size. The range of this value is 10 to 24.
            lgblock: The base-2 logarithm of the maximum input block size. The range of this value is 16 to 24.
                If set to 0, the value will be set based on quality.
        """
        self.app = app
        self.minimum_size = minimum_size
        self.initial_message: Optional["HTTPResponseStartEvent"] = None
        self.started = False
        self.br_buffer = io.BytesIO()
        self.quality = quality
        self.mode = mode
        self.lgwin = lgwin
        self.lgblock = lgblock
        self.br_file = brotli.Compressor(quality=self.quality, mode=self.mode, lgwin=self.lgwin, lgblock=self.lgblock)

    async def __call__(self, scope: "HTTPScope", receive: "Receive", send: "Send") -> None:
        await self.app(scope, receive, self.create_send_wrapper(send))

    def create_send_wrapper(self, send: "Send") -> "Send":
        """Wraps 'send' to handle brotli compression.

        Args:
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """

        async def send_wrapper(message: "Message") -> None:
            """Handles and compresses the HTTP Message with brotli.

            Args:
                message (Message): An ASGI Message.
            """

            if message["type"] == "http.response.start":
                # Don't send the initial message until we've determined how to
                # modify the outgoing headers correctly.
                self.initial_message = message
                return

            initial_message = cast("HTTPResponseStartEvent", self.initial_message)

            if message["type"] == "http.response.body" and not self.started:
                self.started = True
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if len(body) < self.minimum_size and not more_body:
                    # Don't apply Brotli to small outgoing responses.
                    await send(initial_message)
                    await send(message)
                elif not more_body:
                    # Standard Brotli response.
                    body = self.br_file.process(body) + self.br_file.finish()
                    headers = MutableHeaders(raw=initial_message["headers"])
                    headers["Content-Encoding"] = CompressionEncoding.BROTLI
                    headers["Content-Length"] = str(len(body))
                    headers.add_vary_header("Accept-Encoding")
                    message["body"] = body

                    await send(initial_message)
                    await send(message)
                else:
                    # Initial body in streaming Brotli response.
                    headers = MutableHeaders(raw=initial_message["headers"])
                    headers["Content-Encoding"] = CompressionEncoding.BROTLI
                    headers.add_vary_header("Accept-Encoding")
                    del headers["Content-Length"]
                    self.br_buffer.write(self.br_file.process(body) + self.br_file.flush())
                    message["body"] = self.br_buffer.getvalue()
                    self.br_buffer.seek(0)
                    self.br_buffer.truncate()
                    await send(initial_message)
                    await send(message)
            elif message["type"] == "http.response.body":
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
                await send(message)

        return send_wrapper
