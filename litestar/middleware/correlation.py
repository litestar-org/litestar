from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final
from uuid import uuid4

from litestar.connection import ASGIConnection
from litestar.datastructures.headers import Headers, MutableScopeHeaders
from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware
from litestar.types import Empty
from litestar.utils.scope.state import ScopeState

if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.types import ASGIApp, Message, Receive, Scope, Send

__all__ = (
    "TRACE_CONTEXT_FALLBACK_HEADERS",
    "CorrelationMiddleware",
    "get_correlation_id",
)

TRACE_CONTEXT_FALLBACK_HEADERS: Final[tuple[str, ...]] = (
    "x-request-id",
    "x-correlation-id",
    "traceparent",
)

_LOWERCASE_HEX = frozenset("0123456789abcdef")


def get_correlation_id(connection: ASGIConnection[Any, Any, Any, Any] | Scope) -> str | None:
    """Get the correlation ID stored on the connection scope by :class:`CorrelationMiddleware`.

    Args:
        connection: An ASGI connection or scope.

    Returns:
        The correlation ID, or ``None`` if none was set.
    """
    scope = connection.scope if isinstance(connection, ASGIConnection) else connection
    correlation_id = ScopeState.from_scope(scope).correlation_id
    return None if correlation_id is Empty else correlation_id


class CorrelationMiddleware(ASGIMiddleware):
    """ASGI middleware for extracting, generating, and propagating correlation IDs.

    The active correlation ID is stored on the connection scope and can be retrieved
    with :func:`get_correlation_id`.
    """

    scopes = (ScopeType.HTTP, ScopeType.WEBSOCKET)

    def __init__(
        self,
        header_names: Sequence[str] | None = None,
        additional_header_names: Sequence[str] | None = None,
        response_header_name: str | None = "x-request-id",
        max_length: int = 128,
    ) -> None:
        """Initialize CorrelationMiddleware.

        Args:
            header_names: Header name or sequence of header names to inspect in priority order, replacing the defaults.
            additional_header_names: Header name or sequence of header names to inspect after the defaults.
            response_header_name: Optional header name to echo correlation ID in response. Set to None to disable.
            max_length: Maximum length for correlation IDs to prevent log injection.

        Raises:
            ValueError: If ``max_length`` is not positive or both header name options are provided.
        """
        if max_length <= 0:
            raise ValueError("max_length must be greater than 0")
        if header_names is not None and additional_header_names is not None:
            raise ValueError("header_names and additional_header_names are mutually exclusive")
        if header_names is None:
            if isinstance(additional_header_names, str):
                additional_header_names = (additional_header_names,)
            header_names = (*TRACE_CONTEXT_FALLBACK_HEADERS, *(additional_header_names or ()))
        if isinstance(header_names, str):
            header_names = (header_names,)
        normalized_header_names: list[str] = []
        for name in header_names:
            normalized_name = name.strip().casefold()
            if normalized_name and normalized_name not in normalized_header_names:
                normalized_header_names.append(normalized_name)
        self.header_names = tuple(normalized_header_names)
        self.response_header_name = response_header_name.strip().casefold() if response_header_name else None
        self.max_length = max_length

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """ASGI call handler.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
            next_app: The next ASGI application in the middleware stack.
        """
        correlation_id = self._extract_correlation_id(scope)
        ScopeState.from_scope(scope).correlation_id = correlation_id

        if (response_header_name := self.response_header_name) is None:
            await next_app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableScopeHeaders.from_message(message)
                headers[response_header_name] = correlation_id
            await send(message)

        await next_app(scope, receive, send_wrapper)

    def _extract_correlation_id(self, scope: Scope) -> str:
        """Extract correlation ID from incoming request headers or generate fallback.

        Args:
            scope: The ASGI scope.

        Returns:
            Extracted or generated correlation ID.
        """
        headers = Headers.from_scope(scope)
        for name in self.header_names:
            if (value := headers.get(name)) is None:
                continue
            correlation_id = self._parse_traceparent(value) if name == "traceparent" else self._sanitize(value)
            if correlation_id is not None:
                return correlation_id
        return str(uuid4())

    def _parse_traceparent(self, value: str) -> str | None:
        """Defensively parse W3C traceparent header.

        Args:
            value: Incoming traceparent header value.

        Returns:
            The extracted trace ID if valid, else the sanitized raw header string.
        """
        sanitized = _strip_safe_value(value)
        if sanitized is None:
            return None
        parts = sanitized.split("-")
        if len(parts) != 4:
            return sanitized[: self.max_length]
        version, trace_id, parent_id, flags = parts
        if (
            _is_lowercase_hex(version, 2)
            and version != "ff"
            and _is_lowercase_hex(trace_id, 32)
            and trace_id != "0" * 32
            and _is_lowercase_hex(parent_id, 16)
            and parent_id != "0" * 16
            and _is_lowercase_hex(flags, 2)
        ):
            return trace_id[: self.max_length]
        return sanitized[: self.max_length]

    def _sanitize(self, value: str) -> str | None:
        """Sanitize a correlation ID by stripping whitespace and rejecting control characters.

        Args:
            value: Raw correlation ID.

        Returns:
            Sanitized correlation ID, or ``None`` when the value is unsafe.
        """
        sanitized = _strip_safe_value(value)
        return sanitized[: self.max_length] if sanitized is not None else None


def _is_lowercase_hex(value: str, length: int) -> bool:
    return len(value) == length and _LOWERCASE_HEX.issuperset(value)


def _strip_safe_value(value: str) -> str | None:
    value = value.strip()
    if not value or any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    return value
