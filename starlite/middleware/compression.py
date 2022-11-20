from gzip import GzipFile
from io import BytesIO
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union

from starlite.constants import SCOPE_STATE_RESPONSE_COMPRESSED
from starlite.datastructures import Headers, MutableScopeHeaders
from starlite.enums import CompressionEncoding, ScopeType
from starlite.exceptions import MissingDependencyException
from starlite.middleware.base import AbstractMiddleware
from starlite.utils import Ref, set_starlite_scope_state

if TYPE_CHECKING:
    from starlite.config import CompressionConfig
    from starlite.types import (
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


class CompressionFacade:
    """A unified facade offering a uniform interface for different compression libraries."""

    __slots__ = ("compressor", "buffer", "compression_encoding")

    compressor: Union["GzipFile", "Compressor"]  # pyright: ignore

    def __init__(self, buffer: BytesIO, compression_encoding: CompressionEncoding, config: "CompressionConfig") -> None:
        """Initialize `CompressionFacade`.

        Args:
            buffer: A bytes IO buffer to write the compressed data into.
            compression_encoding: The compression encoding used.
            config: The app compression config.
        """
        self.buffer = buffer
        self.compression_encoding = compression_encoding

        if compression_encoding == CompressionEncoding.BROTLI:
            try:
                from brotli import MODE_FONT, MODE_GENERIC, MODE_TEXT, Compressor
            except ImportError as e:
                raise MissingDependencyException("brotli is not installed") from e
            else:
                modes: Dict[Literal["generic", "text", "font"], int] = {
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

    def __init__(self, app: "ASGIApp", config: "CompressionConfig") -> None:
        """Initialize `CompressionMiddleware`

        Args:
            app: The 'next' ASGI app to call.
            config: An instance of CompressionConfig.
        """
        super().__init__(
            app=app, exclude=config.exclude, exclude_opt_key=config.exclude_opt_key, scopes={ScopeType.HTTP}
        )
        self.config = config

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
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
        send: "Send",
        compression_encoding: Literal[CompressionEncoding.BROTLI, CompressionEncoding.GZIP],
        scope: "Scope",
    ) -> "Send":
        """Wrap `send` to handle brotli compression.

        Args:
            send: The ASGI send function.
            compression_encoding: The compression encoding used.
            scope: The ASGI connection scope

        Returns:
            An ASGI send function.
        """

        buffer = BytesIO()
        facade = CompressionFacade(buffer=buffer, compression_encoding=compression_encoding, config=self.config)

        initial_message = Ref[Optional["HTTPResponseStartEvent"]](None)
        started = Ref[bool](False)

        async def send_wrapper(message: "Message") -> None:
            """Handle and compresses the HTTP Message with brotli.

            Args:
                message (Message): An ASGI Message.
            """

            if message["type"] == "http.response.start":
                initial_message.value = message
                return

            if initial_message.value and message["type"] == "http.response.body":
                body = message["body"]
                more_body = message.get("more_body")

                if not started.value:
                    started.value = True
                    if more_body:
                        headers = MutableScopeHeaders(initial_message.value)
                        headers["Content-Encoding"] = compression_encoding
                        headers.extend_header_value("vary", "Accept-Encoding")
                        del headers["Content-Length"]
                        set_starlite_scope_state(scope, SCOPE_STATE_RESPONSE_COMPRESSED, True)

                        facade.write(body)

                        message["body"] = buffer.getvalue()
                        buffer.seek(0)
                        buffer.truncate()
                        await send(initial_message.value)
                        await send(message)

                    elif len(body) >= self.config.minimum_size:
                        facade.write(body)
                        facade.close()
                        body = buffer.getvalue()

                        headers = MutableScopeHeaders(initial_message.value)
                        headers["Content-Encoding"] = compression_encoding
                        headers["Content-Length"] = str(len(body))
                        headers.extend_header_value("vary", "Accept-Encoding")
                        message["body"] = body
                        set_starlite_scope_state(scope, SCOPE_STATE_RESPONSE_COMPRESSED, True)

                        await send(initial_message.value)
                        await send(message)

                    else:
                        await send(initial_message.value)
                        await send(message)

                else:
                    facade.write(body)
                    if not more_body:
                        facade.close()

                    message["body"] = buffer.getvalue()

                    buffer.seek(0)
                    buffer.truncate()

                    if not more_body:
                        buffer.close()

                    await send(message)

        return send_wrapper
