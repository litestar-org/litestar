# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Any, Literal

from litestar.datastructures import Headers, MutableScopeHeaders
from litestar.enums import CompressionEncoding, ScopeType
from litestar.middleware.base import ASGIMiddleware
from litestar.middleware.compression.gzip_facade import GzipCompression
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState

if TYPE_CHECKING:
    from litestar.middleware.compression.facade import CompressionFacade
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


class CompressionMiddleware(ASGIMiddleware):
    """Compression Middleware Wrapper.

    This is a wrapper allowing for generic compression configuration / handler middleware
    """

    scopes = (ScopeType.HTTP, ScopeType.ASGI)

    def __init__(
        self,
        *,
        facade: type[CompressionFacade],
        backend_config: Any = None,
        gzip_fallback: bool = True,
        gzip_backend_config: Any = None,
        minimum_size: int = 500,
        exclude: str | list[str] | None = None,
        exclude_opt_key: str | None = None,
    ) -> None:
        """Initialize ``CompressionMiddleware``

        Args:
            facade: The compression facade to use for the actual compression.
            backend_config: Configuration specific to the compression backend, passed
                through to the facade.
            gzip_fallback: Use GZIP as a fallback if the facade's encoding is not
                supported by the client.
            gzip_backend_config: Configuration passed to the GZIP facade when GZIP is
                used as a fallback for a facade with a different encoding.
            minimum_size: Minimum response size (bytes) to enable compression.
            exclude: A pattern or list of patterns to skip in the compression middleware,
                matched against the handler path.
            exclude_opt_key: An identifier to use on routes to disable compression for a
                particular route.
        """
        self.facade = facade
        self.backend_config = dict(backend_config) if isinstance(backend_config, dict) else backend_config
        self.gzip_fallback = gzip_fallback
        self.gzip_backend_config = (
            dict(gzip_backend_config) if isinstance(gzip_backend_config, dict) else gzip_backend_config
        )
        self.minimum_size = minimum_size
        self.exclude_path_pattern = tuple(exclude) if isinstance(exclude, list) else exclude
        self.exclude_opt_key = exclude_opt_key

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """Handle ASGI call.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
            next_app: The next ASGI application in the middleware stack to call.

        Returns:
            None
        """
        if scope["type"] != ScopeType.HTTP:
            await next_app(scope, receive, send)
            return

        accept_encoding = Headers.from_scope(scope).get("accept-encoding", "")

        if self.facade.encoding in accept_encoding:
            await next_app(
                scope,
                receive,
                self.create_compression_send_wrapper(send=send, compression_encoding=self.facade.encoding, scope=scope),
            )
            return

        if self.gzip_fallback and CompressionEncoding.GZIP in accept_encoding:
            await next_app(
                scope,
                receive,
                self.create_compression_send_wrapper(
                    send=send, compression_encoding=CompressionEncoding.GZIP, scope=scope
                ),
            )
            return

        await next_app(scope, receive, send)

    def create_compression_send_wrapper(
        self,
        send: Send,
        compression_encoding: Literal[CompressionEncoding.BROTLI, CompressionEncoding.GZIP, CompressionEncoding.ZSTD]
        | str,
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

        # We can't use `self.facade` directly if the compression is `gzip` since it may be
        # being used as a fallback.
        if compression_encoding == CompressionEncoding.GZIP:
            backend_config = (
                self.backend_config if self.facade.encoding == CompressionEncoding.GZIP else self.gzip_backend_config
            )
            facade = GzipCompression(
                buffer=bytes_buffer, compression_encoding=compression_encoding, backend_config=backend_config
            )
        else:
            facade = self.facade(  # type: ignore[assignment]
                buffer=bytes_buffer, compression_encoding=compression_encoding, backend_config=self.backend_config
            )

        initial_message: HTTPResponseStartEvent | None = None
        started = False

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
                facade.close()
                return

            if initial_message and message["type"] == "http.disconnect":
                facade.close()
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

                        facade.write(body, final=not more_body)

                        message["body"] = bytes_buffer.getvalue()
                        bytes_buffer.seek(0)
                        bytes_buffer.truncate()
                        await send(initial_message)
                        await send(message)

                    elif len(body) >= self.minimum_size:
                        facade.write(body, final=not more_body)
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
                        facade.close()
                        await send(initial_message)
                        await send(message)

                else:
                    facade.write(body, final=not more_body)
                    if not more_body:
                        facade.close()

                    message["body"] = bytes_buffer.getvalue()

                    bytes_buffer.seek(0)
                    bytes_buffer.truncate()

                    if not more_body:
                        bytes_buffer.close()

                    await send(message)

        return send_wrapper
