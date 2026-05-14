from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Literal

from litestar.exceptions import MissingDependencyException
from litestar.middleware.base import DefineMiddleware
from litestar.plugins.opentelemetry._utils import get_route_details_from_scope
from litestar.plugins.opentelemetry.middleware import (
    OpenTelemetryInstrumentationMiddleware,
)

__all__ = ("OpenTelemetryConfig",)


try:
    import opentelemetry  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("opentelemetry") from e


from opentelemetry.trace import Span, Tracer, TracerProvider

if TYPE_CHECKING:
    from opentelemetry.metrics import Meter, MeterProvider

    from litestar.types import AfterExceptionHookHandler, Scope, Scopes

ServerRequestHookHandler = Callable[[Span, "dict[str, Any]"], None]
"""Hook called with the server span and ASGI scope for every incoming request."""

ClientRequestHookHandler = Callable[[Span, "dict[str, Any]", "dict[str, Any]"], None]
"""Hook called with the internal span, ASGI scope, and ASGI message when ``receive`` is called."""

ClientResponseHookHandler = Callable[[Span, "dict[str, Any]", "dict[str, Any]"], None]
"""Hook called with the internal span, ASGI scope, and ASGI message when ``send`` is called."""


@dataclass
class OpenTelemetryConfig:
    """Configuration class for the OpenTelemetry middleware.

    Consult the `OpenTelemetry ASGI documentation <https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html>`_ for more info about the configuration options.
    """

    after_exception_hook_handler: AfterExceptionHookHandler | None = field(default=None)
    """Callback which is called with the exception and the scope object for every exception raised."""

    scope_span_details_extractor: Callable[[Scope], tuple[str, dict[str, Any]]] = field(
        default=get_route_details_from_scope
    )
    """Callback which should return a string and a tuple, representing the desired default span name and a dictionary
    with any additional span attributes to set.
    """
    server_request_hook_handler: ServerRequestHookHandler | None = field(default=None)
    """Optional callback which is called with the server span and ASGI scope object for every incoming request."""
    client_request_hook_handler: ClientRequestHookHandler | None = field(default=None)
    """Optional callback which is called with the internal span, ASGI scope, and ASGI message when ``receive`` is
    called.
    """
    client_response_hook_handler: ClientResponseHookHandler | None = field(default=None)
    """Optional callback which is called with the internal span, ASGI scope, and ASGI message when ``send`` is called."""
    meter_provider: MeterProvider | None = field(default=None)
    """Optional meter provider to use.

    If omitted the current globally configured one is used.
    """
    tracer_provider: TracerProvider | None = field(default=None)
    """Optional tracer provider to use.

    If omitted the current globally configured one is used.
    """
    tracer: Tracer | None = field(default=None)
    """Optional pre-built tracer instance to use.

    If omitted, a tracer will be created from the tracer provider.
    """
    meter: Meter | None = field(default=None)
    """Optional meter to use.

    If omitted the provided meter provider or the global one will be used.
    """
    exclude: str | list[str] | None = field(default=None)
    """A pattern or list of patterns to skip in the Allowed Hosts middleware."""
    exclude_opt_key: str | None = field(default=None)
    """An identifier to use on routes to disable hosts check for a particular route."""
    exclude_urls_env_key: str = "LITESTAR"
    """Key to use when checking whether a list of excluded urls is passed via ENV.

    OpenTelemetry supports excluding urls by passing an env in the format '{exclude_urls_env_key}_EXCLUDED_URLS'. With
    the default being ``LITESTAR_EXCLUDED_URLS``.
    """
    exclude_spans: list[Literal["receive", "send"]] | None = None
    """Optionally exclude HTTP send and/or receive spans from the trace."""
    scopes: Scopes | None = field(default=None)
    """ASGI scopes processed by the middleware, if None both ``http`` and ``websocket`` will be processed."""
    http_capture_headers_server_request: list[str] | None = field(default=None)
    """List of request headers to capture as span attributes."""
    http_capture_headers_server_response: list[str] | None = field(default=None)
    """List of response headers to capture as span attributes."""
    http_capture_headers_sanitize_fields: list[str] | None = field(default=None)
    """List of header names whose values will be replaced with ``[REDACTED]`` in span attributes."""
    middleware_class: type[OpenTelemetryInstrumentationMiddleware] = field(
        default=OpenTelemetryInstrumentationMiddleware
    )
    """The middleware class to use.

    Should be a subclass of
    :class:`OpenTelemetryInstrumentationMiddleware <litestar.plugins.opentelemetry.OpenTelemetryInstrumentationMiddleware>`.
    """

    @property
    def middleware(self) -> DefineMiddleware:
        """Create an instance of :class:`DefineMiddleware <litestar.middleware.base.DefineMiddleware>`.

        Returns:
            An instance of ``DefineMiddleware``.
        """
        return DefineMiddleware(self.middleware_class, config=self)
