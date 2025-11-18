"""OpenTelemetry instrumentation helpers for Litestar constructs.

This module provides optional instrumentation for Litestar-specific features like guards,
lifecycle events, dependency injection, and channels. All functions gracefully handle
cases where OpenTelemetry is not installed.
"""

from __future__ import annotations

import inspect
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from litestar.connection import ASGIConnection
    from litestar.handlers.base import BaseRouteHandler
__all__ = (
    "create_span",
    "instrument_channel_operation",
    "instrument_dependency",
    "instrument_guard",
    "instrument_lifecycle_event",
)

# Global flag to track if OTEL is available
_OTEL_AVAILABLE: bool | None = None
try:  # pragma: no cover - optional dependency
    from opentelemetry.trace import TracerProvider as _RuntimeTracerProvider
except ImportError:  # pragma: no cover
    _RuntimeTracerProvider = object  # type: ignore[misc,assignment]

_CUSTOM_TRACER_PROVIDER: _RuntimeTracerProvider | None = None  # pyright: ignore


def _get_tracer(name: str) -> Any:
    from opentelemetry import trace

    tracer_provider = _CUSTOM_TRACER_PROVIDER or trace.get_tracer_provider()
    return tracer_provider.get_tracer(name)


def _is_otel_available() -> bool:
    """Check if OpenTelemetry is installed and available."""
    global _OTEL_AVAILABLE
    if _OTEL_AVAILABLE is not None:
        return _OTEL_AVAILABLE

    try:
        import opentelemetry  # noqa: F401

        _OTEL_AVAILABLE = True
    except ImportError:
        _OTEL_AVAILABLE = False

    return _OTEL_AVAILABLE


@contextmanager
def create_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[Any, None, None]:
    """Create an OTEL span if OpenTelemetry is available.

    Args:
        name: The span name
        attributes: Optional attributes to add to the span

    Yields:
        The span object if OTEL is available, otherwise None
    """
    if not _is_otel_available():
        yield None
        return

    from opentelemetry.trace import Status, StatusCode

    tracer = _get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            span.set_attributes(attributes)

        try:
            yield span
        except Exception as exc:
            if span.is_recording():
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


@asynccontextmanager
async def create_span_async(name: str, attributes: dict[str, Any] | None = None) -> AsyncGenerator[Any, None]:
    """Create an OTEL span if OpenTelemetry is available (async version).

    Args:
        name: The span name
        attributes: Optional attributes to add to the span

    Yields:
        The span object if OTEL is available, otherwise None
    """
    if not _is_otel_available():
        yield None
        return

    from opentelemetry.trace import Status, StatusCode

    tracer = _get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            span.set_attributes(attributes)

        try:
            yield span
        except Exception as exc:
            if span.is_recording():
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def instrument_guard(guard_func: Callable) -> Callable:
    """Instrument a guard function with OpenTelemetry tracing.

    Args:
        guard_func: The guard function to instrument

    Returns:
        The instrumented guard function (or original if OTEL not available)
    """
    if not _is_otel_available():
        return guard_func

    @wraps(guard_func)
    async def instrumented_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
        guard_name = getattr(guard_func, "__name__", str(guard_func))
        handler_name = route_handler.handler_name if hasattr(route_handler, "handler_name") else str(route_handler)

        async with create_span_async(
            f"guard.{guard_name}",
            attributes={
                "litestar.guard.name": guard_name,
                "litestar.handler.name": handler_name,
                "litestar.connection.type": connection.scope.get("type", "unknown"),
            },
        ):
            await guard_func(connection, route_handler)

    return instrumented_guard


def instrument_lifecycle_event(event_name: str) -> Callable:
    """Decorator to instrument lifecycle events (startup/shutdown).

    Args:
        event_name: Name of the lifecycle event (e.g., "startup", "shutdown")

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        if not _is_otel_available():
            return func

        @wraps(func)
        async def instrumented_event(*args: Any, **kwargs: Any) -> Any:
            func_name = getattr(func, "__name__", str(func))

            async with create_span_async(
                f"lifecycle.{event_name}.{func_name}",
                attributes={
                    "litestar.lifecycle.event": event_name,
                    "litestar.lifecycle.handler": func_name,
                },
            ):
                return await func(*args, **kwargs)

        return instrumented_event

    return decorator


def instrument_dependency(dependency_key: str, provider_func: Callable | None = None) -> Callable:
    """Instrument a dependency provider with OpenTelemetry tracing.

    Args:
        dependency_key: The dependency injection key
        provider_func: The provider function to instrument

    Returns:
        The instrumented provider function (or original if OTEL not available)
    """
    if provider_func is None:
        return lambda fn: instrument_dependency(dependency_key, fn)

    if not _is_otel_available():
        return provider_func

    @wraps(provider_func)
    async def instrumented_provider(*args: Any, **kwargs: Any) -> Any:
        provider_name = getattr(provider_func, "__name__", str(provider_func))

        async with create_span_async(
            f"dependency.{dependency_key}",
            attributes={
                "litestar.dependency.key": dependency_key,
                "litestar.dependency.provider": provider_name,
            },
        ) as span:
            result = provider_func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result

            # Add result type as attribute
            if span and span.is_recording():
                span.set_attribute("litestar.dependency.result_type", type(result).__name__)

            return result

    return instrumented_provider


def instrument_channel_operation(operation: str, channel: str) -> Callable:
    """Decorator to instrument channel pub/sub operations.

    Args:
        operation: The operation type ("publish", "subscribe")
        channel: The channel name

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        if not _is_otel_available():
            return func

        @wraps(func)
        async def instrumented_operation(*args: Any, **kwargs: Any) -> Any:
            async with create_span_async(
                f"channel.{operation}",
                attributes={
                    "litestar.channel.operation": operation,
                    "litestar.channel.name": channel,
                },
            ):
                return await func(*args, **kwargs)

        return instrumented_operation

    return decorator
