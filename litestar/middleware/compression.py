from __future__ import annotations

from gzip import GzipFile
from io import BytesIO
from typing import TYPE_CHECKING, Any, Literal

from litestar.datastructures import Headers, MutableScopeHeaders
from litestar.enums import CompressionEncoding, ScopeType
from litestar.exceptions import MissingDependencyException
from litestar.middleware.base import AbstractMiddleware
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState

if TYPE_CHECKING:
    from litestar.config.compression import CompressionConfig
    from litestar.types import (
        ASGIApp,
        HTTPResponseStartEvent,
        Message,
        Receive,
        Scope,
        Send,
    )

    try:
        from brotli import Compressor
    except ImportError:
        Compressor = Any

__all__ = ("CompressionFacade", "CompressionMiddleware")


class CompressionFacade:
    """A unified facade offering a uniform interface for different compression libraries."""

    __slots__ = ("compressor", "buffer", "compression_encoding")

    compressor: GzipFile | Compressor  # pyright: ignore

    def __init__(self, buffer: BytesIO, compression_encoding: CompressionEncoding, config: CompressionConfig) -> None:
        """Initialize ``CompressionFacade``.

        Args:
            buffer: A bytes IO buffer to write the compressed data into.
            compression_encoding: The compression encoding used.
            config: The app compression config.
        """
        self.buffer = buffer
        self.compression_encoding = compression_encoding

        if compression_encoding == CompressionEncoding.BROTLI:
            try:
                import brotli  # noqa: F401
            except ImportError as e:
                raise MissingDependencyException("brotli") from e

            from brotli import MODE_FONT, MODE_GENERIC, MODE_TEXT, Compressor

            modes: dict[Literal["generic", "text", "font"], int] = {
                "text": int(MODE_TEXT),
                "font": int(MODE_FONT),
                "generic": int(MODE_GENERIC),
            }
            self.compressor = Compressor(
                quality=config.brotli_quality,
                mode=modes[config.brotli_mode],
                lgwin=config.brotli_lgwin,
                lgblock=config.brotli_lgblock,
            )
        else:
            self.compressor = GzipFile(mode="wb", fileobj=buffer, compresslevel=config.gzip_compress_level)

    def write(self, body: bytes) -> None:
        """Write compressed bytes.

        Args:
            body: Message body to process

        Returns:
            None
        """

        if self.compression_encoding == CompressionEncoding.BROTLI:
            self.buffer.write(self.compressor.process(body) + self.compressor.flush())  # type: ignore
        else:
            self.compressor.write(body)
            self.compressor.flush()

    def close(self) -> None:
        """Close the compression stream.

        Returns:
            None
        """
        if self.compression_encoding == CompressionEncoding.BROTLI:
            self.buffer.write(self.compressor.finish())  # type: ignore
        else:
            self.compressor.close()


class CompressionMiddleware(AbstractMiddleware):
    """Compression Middleware Wrapper.

    This is a wrapper allowing for generic compression configuration / handler middleware
    """

    def __init__(self, app: ASGIApp, config: CompressionConfig) -> None:
        """Initialize ``CompressionMiddleware``

        Args:
            app: The ``next`` ASGI app to call.
            config: An instance of CompressionConfig.
        """
        super().__init__(
            app=app, exclude=config.exclude, exclude_opt_key=config.exclude_opt_key, scopes={ScopeType.HTTP}
        )
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        accept_encoding = Headers.from_scope(scope).get("accept-encoding", "")

        if CompressionEncoding.BROTLI in accept_encoding and self.config.backend == "brotli":
            await self.app(
                scope,
                receive,
                self.create_compression_send_wrapper(
                    send=send, compression_encoding=CompressionEncoding.BROTLI, scope=scope
                ),
            )
            return

        if CompressionEncoding.GZIP in accept_encoding and (
            self.config.backend == "gzip" or self.config.brotli_gzip_fallback
        ):
            await self.app(
                scope,
                receive,
                self.create_compression_send_wrapper(
                    send=send, compression_encoding=CompressionEncoding.GZIP, scope=scope
                ),
            )
            return

        await self.app(scope, receive, send)

    def create_compression_send_wrapper(
        self,
        send: Send,
        compression_encoding: Literal[CompressionEncoding.BROTLI, CompressionEncoding.GZIP],
        scope: Scope,
    ) -> Send:
        """Wrap ``send`` to handle brotli compression.

        Args:
            send: The ASGI send function.
            compression_encoding: The compression encoding used.
            scope: The ASGI connection scope

        Returns:
            An ASGI send function.
        """
        bytes_buffer = BytesIO()
        facade = CompressionFacade(buffer=bytes_buffer, compression_encoding=compression_encoding, config=self.config)

        initial_message: HTTPResponseStartEvent | None = None
        started = False

        _own_encoding = compression_encoding.encode("latin-1")

        connection_state = ScopeState.from_scope(scope)

        async def send_wrapper(message: Message) -> None:
            """Handle and compresses the HTTP Message with brotli.

            Args:
                message (Message): An ASGI Message.
            """
            nonlocal started
            nonlocal initial_message

            if message["type"] == "http.response.start":
                initial_message = message
                return

            if initial_message is not None and value_or_default(connection_state.is_cached, False):
                await send(initial_message)
                await send(message)
                return

            if initial_message and message["type"] == "http.response.body":
                body = message["body"]
                more_body = message.get("more_body")

                if not started:
                    started = True
                    if more_body:
                        headers = MutableScopeHeaders(initial_message)
                        headers["Content-Encoding"] = compression_encoding
                        headers.extend_header_value("vary", "Accept-Encoding")
                        del headers["Content-Length"]
                        connection_state.response_compressed = True

                        facade.write(body)

                        message["body"] = bytes_buffer.getvalue()
                        bytes_buffer.seek(0)
                        bytes_buffer.truncate()
                        await send(initial_message)
                        await send(message)

                    elif len(body) >= self.config.minimum_size:
                        facade.write(body)
                        facade.close()
                        body = bytes_buffer.getvalue()

                        headers = MutableScopeHeaders(initial_message)
                        headers["Content-Encoding"] = compression_encoding
                        headers["Content-Length"] = str(len(body))
                        headers.extend_header_value("vary", "Accept-Encoding")
                        message["body"] = body
                        connection_state.response_compressed = True

                        await send(initial_message)
                        await send(message)

                    else:
                        await send(initial_message)
                        await send(message)

                else:
                    facade.write(body)
                    if not more_body:
                        facade.close()

                    message["body"] = bytes_buffer.getvalue()

                    bytes_buffer.seek(0)
                    bytes_buffer.truncate()

                    if not more_body:
                        bytes_buffer.close()

                    await send(message)

        return send_wrapper
