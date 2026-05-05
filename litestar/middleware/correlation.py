"""W3C Trace Context correlation middleware.

Reads a correlation/trace ID from a configurable list of request headers
(W3C ``traceparent`` first, then cloud-vendor and generic fallbacks), generates
a W3C-compliant ``traceparent`` value when none match, and propagates the
result through a :class:`contextvars.ContextVar` so handlers and loggers can
read it.

The middleware is a *propagation primitive*. It stores the **entire raw header
value** in the context — including the W3C ``version-trace_id-parent_id-flags``
quadruple, or the full vendor format (e.g. AWS ``Root=...;Parent=...;Sampled=...``).
This keeps downstream services able to forward the value verbatim and preserves
the sample-flag bit. Users who want only the 32-character trace ID for log
records can call :func:`trace_id_from_traceparent` themselves.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING, Final
from uuid import uuid4

from litestar.datastructures import Headers
from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware

if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.types.asgi_types import ASGIApp, Receive, Scope, Send

__all__ = (
    "TRACE_CONTEXT_FALLBACK_HEADERS",
    "CorrelationContext",
    "CorrelationMiddleware",
    "trace_id_from_traceparent",
)

logger = logging.getLogger("litestar")

TRACE_CONTEXT_FALLBACK_HEADERS: Final[tuple[str, ...]] = (
    "traceparent",
    "x-amzn-trace-id",
    "x-cloud-trace-context",
    "x-correlation-id",
    "x-request-id",
)
"""Priority-ordered fallback header list scanned when ``auto_trace_headers`` is enabled."""

_W3C_TRACEPARENT_HEADER: Final[str] = "traceparent"
_W3C_TRACE_ID_HEX_LEN: Final[int] = 32
_W3C_PARENT_ID_HEX_LEN: Final[int] = 16
_W3C_VERSION_HEX_LEN: Final[int] = 2
_W3C_FLAGS_HEX_LEN: Final[int] = 2
_W3C_INVALID_VERSION: Final[str] = "ff"
"""Per W3C Trace Context spec section 3.2.1, version ``ff`` is reserved as invalid."""


_correlation_id_var: ContextVar[str | None] = ContextVar("litestar_correlation_id", default=None)


class CorrelationContext:
    """Static accessor over the per-request correlation ID context variable.

    Use :meth:`get` from inside a route handler, dependency, or logger filter to
    read the correlation ID set by :class:`CorrelationMiddleware` for the
    current request. Outside of a request scope, :meth:`get` returns ``None``.
    """

    @staticmethod
    def get() -> str | None:
        """Return the correlation ID for the current request, or ``None`` if unset."""
        return _correlation_id_var.get()

    @staticmethod
    def set(value: str) -> Token[str | None]:
        """Set the correlation ID. Returns a token usable with :meth:`reset`."""
        return _correlation_id_var.set(value)

    @staticmethod
    def reset(token: Token[str | None]) -> None:
        """Reset the correlation ID to its prior value using a token from :meth:`set`."""
        _correlation_id_var.reset(token)


def _is_valid_traceparent(value: str) -> bool:
    """Return ``True`` if ``value`` matches the W3C ``traceparent`` format.

    Format: ``<version>-<trace_id>-<parent_id>-<flags>`` where each part is
    lowercase hex of length 2/32/16/2. Version ``ff`` is reserved as invalid
    per the spec, and trace ID and parent ID must not be all zeros. Never
    raises.
    """
    parts = value.split("-")
    if len(parts) != 4:
        return False
    version, trace_id, parent_id, flags = parts
    if (
        len(version) != _W3C_VERSION_HEX_LEN
        or len(trace_id) != _W3C_TRACE_ID_HEX_LEN
        or len(parent_id) != _W3C_PARENT_ID_HEX_LEN
        or len(flags) != _W3C_FLAGS_HEX_LEN
    ):
        return False
    if version.lower() == _W3C_INVALID_VERSION:
        return False
    try:
        int(version, 16)
        int(trace_id, 16)
        int(parent_id, 16)
        int(flags, 16)
    except ValueError:
        return False
    if int(trace_id, 16) == 0 or int(parent_id, 16) == 0:
        return False
    return True


def trace_id_from_traceparent(value: str) -> str | None:
    """Extract the 32-character trace ID from a W3C ``traceparent`` value.

    Returns the trace-ID hex string if ``value`` is a well-formed traceparent,
    otherwise ``None``. Never raises. Useful for log records that want only the
    trace ID without the parent-span and flags suffix.
    """
    if not _is_valid_traceparent(value):
        return None
    return value.split("-", 2)[1]


def _generate_w3c_traceparent() -> str:
    """Generate a fresh W3C-compliant ``traceparent`` string.

    Returned in the form ``00-<32 hex>-<16 hex>-01`` so it can be forwarded
    verbatim as a ``traceparent`` header to downstream services. The sampled
    flag is set so the trace is recorded.
    """
    return f"00-{uuid4().hex}-{uuid4().hex[:_W3C_PARENT_ID_HEX_LEN]}-01"


class CorrelationMiddleware(ASGIMiddleware):
    """ASGI middleware that propagates a W3C trace context / correlation ID.

    On each request the middleware scans, in order, ``header`` and then (if
    ``auto_trace_headers`` is true) the entries of ``fallback_headers``. The
    first present header's value is stored verbatim in :class:`CorrelationContext`
    for the duration of the request. If no header is present, a fresh
    W3C-compliant ``traceparent`` string is generated.

    A malformed ``traceparent`` (one that fails W3C validation) is logged at
    DEBUG level and stored as-is — the middleware never raises on bad input.

    The stored value is the **entire raw header**, preserving everything needed
    for downstream propagation. Use :func:`trace_id_from_traceparent` if you
    need only the 32-character trace ID portion.
    """

    scopes = (ScopeType.HTTP, ScopeType.WEBSOCKET)

    def __init__(
        self,
        header: str = _W3C_TRACEPARENT_HEADER,
        fallback_headers: Sequence[str] = TRACE_CONTEXT_FALLBACK_HEADERS,
        auto_trace_headers: bool = True,
    ) -> None:
        """Initialize the middleware.

        Args:
            header: Primary header to read the correlation ID from.
            fallback_headers: Additional headers to consult, in priority order,
                when ``auto_trace_headers`` is true and ``header`` is absent.
            auto_trace_headers: If true, scan ``fallback_headers`` after
                ``header``. If false, only ``header`` is consulted.
        """
        self.header = header.lower()
        self.fallback_headers = tuple(h.lower() for h in fallback_headers)
        self.auto_trace_headers = auto_trace_headers
        # Pre-compute the deduplicated header lookup order once at construction
        # time. ASGI middleware runs on every request, so doing this in
        # ``handle`` would be wasteful.
        self._resolved_headers: tuple[str, ...] = self._compute_resolved_headers()

    def _compute_resolved_headers(self) -> tuple[str, ...]:
        if not self.auto_trace_headers:
            return (self.header,)
        seen: set[str] = set()
        ordered: list[str] = []
        for name in (self.header, *self.fallback_headers):
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    def _extract_value(self, headers: Headers) -> str:
        for name in self._resolved_headers:
            value = headers.get(name)
            if value is None:
                continue
            if name == _W3C_TRACEPARENT_HEADER and not _is_valid_traceparent(value):
                logger.debug("Malformed traceparent header %r; storing raw value", value)
            return value
        return _generate_w3c_traceparent()

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        value = self._extract_value(Headers.from_scope(scope))
        token = CorrelationContext.set(value)
        try:
            await next_app(scope, receive, send)
        finally:
            CorrelationContext.reset(token)
