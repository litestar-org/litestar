from collections.abc import Generator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING, Final
from uuid import uuid4

from litestar.datastructures.headers import MutableScopeHeaders

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Message, Receive, Scope, Send

__all__ = (
    "TRACE_CONTEXT_FALLBACK_HEADERS",
    "CorrelationContext",
    "CorrelationMiddleware",
)

TRACE_CONTEXT_FALLBACK_HEADERS: Final[tuple[str, ...]] = (
    "x-request-id",
    "x-correlation-id",
    "traceparent",
    "x-cloud-trace-context",
    "grpc-trace-bin",
    "x-amzn-trace-id",
    "x-b3-traceid",
    "x-client-trace-id",
)

_correlation_id_var: ContextVar[str | None] = ContextVar("litestar_correlation_id", default=None)
_LOWERCASE_HEX = frozenset("0123456789abcdef")
_MISSING = object()


def _is_lowercase_hex(value: str, length: int) -> bool:
    return len(value) == length and not _LOWERCASE_HEX.difference(value)


def _strip_safe_value(value: str) -> str | None:
    value = value.strip()
    if not value or any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    return value


class CorrelationContext:
    """Context manager and accessor for correlation ID tracking."""

    __slots__ = ()

    @classmethod
    def get(cls) -> str | None:
        """Get the current correlation ID.

        Returns:
            The current correlation ID or None if not set.
        """
        return _correlation_id_var.get()

    @classmethod
    def set(cls, value: str | None) -> Token[str | None]:
        """Set the current correlation ID.

        Args:
            value: Correlation ID value to set.

        Returns:
            A ContextVar Token for resetting context.
        """
        return _correlation_id_var.set(value)

    @classmethod
    def reset(cls, token: Token[str | None]) -> None:
        """Reset the correlation ID using a token.

        Args:
            token: ContextVar token returned from set().
        """
        _correlation_id_var.reset(token)

    @classmethod
    def clear(cls) -> None:
        """Clear the current correlation ID."""
        _correlation_id_var.set(None)

    @classmethod
    def generate(cls) -> str:
        """Generate a new correlation ID UUID.

        Returns:
            A stringified UUID4.
        """
        return str(uuid4())

    @classmethod
    @contextmanager
    def context(cls, value: str | None = None) -> Generator[str, None, None]:
        """Context manager for correlation ID tracking.

        Args:
            value: Optional correlation ID to use. If None, generates a new one.

        Yields:
            The active correlation ID.
        """
        if value is None:
            value = cls.generate()
        token = cls.set(value)
        try:
            yield value
        finally:
            cls.reset(token)


class CorrelationMiddleware:
    """ASGI middleware for extracting, generating, and propagating correlation IDs."""

    __slots__ = ("app", "header_names", "max_length", "response_header_name")

    def __init__(
        self,
        app: "ASGIApp",
        header_names: Sequence[str] = TRACE_CONTEXT_FALLBACK_HEADERS,
        response_header_name: str | None = "x-request-id",
        max_length: int = 128,
    ) -> None:
        """Initialize CorrelationMiddleware.

        Args:
            app: The ASGI application.
            header_names: Header name or sequence of header names to inspect in priority order.
            response_header_name: Optional header name to echo correlation ID in response. Set to None to disable.
            max_length: Maximum length for correlation IDs to prevent log injection.
        """
        if max_length <= 0:
            raise ValueError("max_length must be greater than 0")
        if isinstance(header_names, str):
            header_names = (header_names,)
        normalized_header_names: list[str] = []
        for name in header_names:
            normalized_name = name.strip().casefold()
            if normalized_name and normalized_name not in normalized_header_names:
                normalized_header_names.append(normalized_name)
        self.app = app
        self.header_names = tuple(normalized_header_names)
        self.response_header_name = response_header_name.strip().casefold() if response_header_name else None
        self.max_length = max_length

    def _sanitize(self, value: str) -> str | None:
        """Sanitize a correlation ID by stripping whitespace and rejecting control characters.

        Args:
            value: Raw correlation ID.

        Returns:
            Sanitized correlation ID, or ``None`` when the value is unsafe.
        """
        sanitized = _strip_safe_value(value)
        return sanitized[: self.max_length] if sanitized is not None else None

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

    def _extract_correlation_id(self, scope: "Scope") -> str:
        """Extract correlation ID from incoming request headers or generate fallback.

        Args:
            scope: The ASGI scope.

        Returns:
            Extracted or generated correlation ID.
        """
        for name in self.header_names:
            name_bytes = name.encode("latin-1")
            for raw_name, raw_value in scope.get("headers", ()):
                if raw_name.lower() != name_bytes:
                    continue
                value = raw_value.decode("latin-1")
                correlation_id = self._parse_traceparent(value) if name == "traceparent" else self._sanitize(value)
                if correlation_id is not None:
                    return correlation_id
        return CorrelationContext.generate()

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI call handler.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        correlation_id = self._extract_correlation_id(scope)
        token = CorrelationContext.set(correlation_id)
        state = scope.setdefault("state", {})
        previous_correlation_id = state.get("correlation_id", _MISSING)
        state["correlation_id"] = correlation_id

        async def send_wrapper(message: "Message") -> None:
            if message["type"] == "http.response.start" and self.response_header_name:
                headers = MutableScopeHeaders.from_message(message)
                headers[self.response_header_name] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            CorrelationContext.reset(token)
            if previous_correlation_id is _MISSING:
                state.pop("correlation_id", None)
            else:
                state["correlation_id"] = previous_correlation_id
