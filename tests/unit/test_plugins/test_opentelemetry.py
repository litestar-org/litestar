"""Tests for enhanced OpenTelemetry instrumentation features."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.usefixtures("reset_opentelemetry_tracer_provider")


@pytest.fixture
def reset_opentelemetry_tracer_provider() -> None:
    """Reset the OpenTelemetry tracer provider after each test."""
    from opentelemetry import trace

    from litestar.plugins.opentelemetry import instrumentation

    # Reset the global tracer provider
    if hasattr(trace, "_TRACER_PROVIDER"):
        setattr(trace, "_TRACER_PROVIDER", None)
    if hasattr(trace, "_TRACER_PROVIDER_SET"):
        setattr(trace, "_TRACER_PROVIDER_SET", False)
    instrumentation._CUSTOM_TRACER_PROVIDER = None
    instrumentation._OTEL_AVAILABLE = None


def test_exception_recording_in_middleware() -> None:
    """Test that exceptions are recorded with full stack traces."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar import get
    from litestar.plugins.opentelemetry import OpenTelemetryConfig
    from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
    from litestar.testing import create_test_client

    # Create an in-memory span exporter to capture traces
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    @get("/error")
    def error_handler() -> None:
        raise ValueError("Test error for OTEL")

    with create_test_client(
        route_handlers=[error_handler],
        plugins=[OpenTelemetryConfig(tracer_provider=tracer_provider).plugin],
    ) as client:
        response = client.get("/error")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR

        # Verify that spans were created and exceptions were recorded
        spans = span_exporter.get_finished_spans()
        assert spans

    # Find the span that should have recorded the exception
    exception_spans = [span for span in spans if span.events]
    assert len(exception_spans) > 0, "Expected at least one span with exception events"

    # Verify exception was recorded
    for span in exception_spans:
        for event in span.events:
            if event.name == "exception":
                attrs = event.attributes or {}
                assert attrs.get("exception.message") == "Test error for OTEL"
                assert attrs.get("exception.type") == "ValueError"
                break
        else:
            continue
        break
    else:
        pytest.fail("No exception event found in spans")


def test_exception_recording_with_http_exception() -> None:
    """Test that HTTP exceptions are also recorded."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar import get
    from litestar.exceptions import NotAuthorizedException
    from litestar.plugins.opentelemetry import OpenTelemetryConfig
    from litestar.status_codes import HTTP_401_UNAUTHORIZED
    from litestar.testing import create_test_client

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    @get("/unauthorized")
    def unauthorized_handler() -> None:
        raise NotAuthorizedException("Not authorized")

    with create_test_client(
        route_handlers=[unauthorized_handler],
        plugins=[OpenTelemetryConfig(tracer_provider=tracer_provider).plugin],
    ) as client:
        response = client.get("/unauthorized")
        assert response.status_code == HTTP_401_UNAUTHORIZED

        spans = span_exporter.get_finished_spans()
        assert spans


def test_middleware_without_exceptions() -> None:
    """Test that middleware works correctly when no exceptions occur."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar import get
    from litestar.plugins.opentelemetry import OpenTelemetryConfig
    from litestar.status_codes import HTTP_200_OK
    from litestar.testing import create_test_client

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    @get("/success")
    def success_handler() -> dict:
        return {"status": "ok"}

    with create_test_client(
        route_handlers=[success_handler],
        plugins=[OpenTelemetryConfig(tracer_provider=tracer_provider).plugin],
    ) as client:
        response = client.get("/success")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"status": "ok"}

    spans = span_exporter.get_finished_spans()
    assert len(spans) > 0

    # Verify no exception events
    for span in spans:
        exception_events = [event for event in span.events if event.name == "exception"]
        assert len(exception_events) == 0


def test_instrumentation_helpers_without_otel() -> None:
    """Test that instrumentation helpers work gracefully without OpenTelemetry installed."""
    from litestar.plugins.opentelemetry import instrumentation

    instrumentation._OTEL_AVAILABLE = False  # Simulate missing dependency

    from litestar.plugins.opentelemetry import create_span

    with create_span("test.span") as span:
        assert span is None  # Should return None when OTEL not available

    instrumentation._OTEL_AVAILABLE = None


def test_guard_instrumentation() -> None:
    """Test that guard functions can be instrumented."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar import get
    from litestar.connection import ASGIConnection
    from litestar.exceptions import NotAuthorizedException
    from litestar.handlers.base import BaseRouteHandler
    from litestar.plugins.opentelemetry import OpenTelemetryConfig, instrument_guard
    from litestar.testing import create_test_client

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    @instrument_guard
    async def test_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
        if not connection.headers.get("x-api-key"):
            raise NotAuthorizedException("API key required")

    @get("/protected", guards=[test_guard])
    def protected_handler() -> dict:
        return {"status": "protected"}

    with create_test_client(
        route_handlers=[protected_handler],
        plugins=[OpenTelemetryConfig(tracer_provider=tracer_provider).plugin],
    ) as client:
        # Test without API key (should fail)
        response = client.get("/protected")
        assert response.status_code == 401

        # Clear spans
        span_exporter.clear()

        # Test with API key (should succeed)
        response = client.get("/protected", headers={"x-api-key": "test-key"})
        assert response.status_code == 200

    spans = span_exporter.get_finished_spans()
    guard_spans = [span for span in spans if "guard" in span.name]
    assert len(guard_spans) > 0, "Expected at least one guard span"


def test_guard_instrumentation_config_opt_in() -> None:
    """Guard spans are created when config.instrument_guards is enabled without decorators."""

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar import get
    from litestar.connection import ASGIConnection
    from litestar.exceptions import NotAuthorizedException
    from litestar.handlers.base import BaseRouteHandler
    from litestar.plugins.opentelemetry import OpenTelemetryConfig
    from litestar.testing import create_test_client

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    async def plain_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
        if not connection.headers.get("x-api-key"):
            raise NotAuthorizedException("API key required")

    @get("/protected", guards=[plain_guard])
    def protected_handler() -> dict:
        return {"status": "protected"}

    config = OpenTelemetryConfig(tracer_provider=tracer_provider, instrument_guards=True)

    with create_test_client(route_handlers=[protected_handler], plugins=[config.plugin]) as client:
        client.get("/protected", headers={"x-api-key": "test"})

    spans = span_exporter.get_finished_spans()
    guard_spans = [span for span in spans if span.name.startswith("guard.")]
    assert guard_spans, "Expected guard spans when instrument_guards is enabled"


def test_dependency_instrumentation() -> None:
    """Test that dependency providers can be instrumented."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar import get
    from litestar.di import Provide
    from litestar.plugins.opentelemetry import OpenTelemetryConfig, instrument_dependency
    from litestar.testing import create_test_client

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    @instrument_dependency("test_dependency")
    async def test_dependency_provider() -> dict:
        return {"value": "test"}

    @get("/with-dependency")
    def handler_with_dependency(test_dependency: dict) -> dict:
        return test_dependency

    with create_test_client(
        route_handlers=[handler_with_dependency],
        dependencies={"test_dependency": Provide(test_dependency_provider)},
        plugins=[OpenTelemetryConfig(tracer_provider=tracer_provider).plugin],
    ) as client:
        response = client.get("/with-dependency")
        assert response.status_code == 200
        assert response.json() == {"value": "test"}

    spans = span_exporter.get_finished_spans()
    dependency_spans = [span for span in spans if "dependency" in span.name]
    assert len(dependency_spans) > 0, "Expected at least one dependency span"


def test_lifecycle_event_instrumentation() -> None:
    """Test that lifecycle events can be instrumented."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar.plugins.opentelemetry import OpenTelemetryConfig, instrument_lifecycle_event
    from litestar.testing import create_test_client

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    startup_called = False
    shutdown_called = False

    @instrument_lifecycle_event("startup")
    async def on_startup() -> None:
        nonlocal startup_called
        startup_called = True

    @instrument_lifecycle_event("shutdown")
    async def on_shutdown() -> None:
        nonlocal shutdown_called
        shutdown_called = True

    with create_test_client(
        route_handlers=[],
        on_startup=[on_startup],
        on_shutdown=[on_shutdown],
        plugins=[OpenTelemetryConfig(tracer_provider=tracer_provider).plugin],
    ):
        pass

    assert startup_called
    assert shutdown_called

    spans = span_exporter.get_finished_spans()
    lifecycle_spans = [span for span in spans if "lifecycle" in span.name]
    assert len(lifecycle_spans) >= 2, "Expected at least startup and shutdown spans"


def test_create_span_context_manager() -> None:
    """Test the create_span context manager."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar.plugins.opentelemetry import create_span

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    from opentelemetry import trace

    trace._TRACER_PROVIDER = tracer_provider
    trace.set_tracer_provider(tracer_provider)

    with create_span("test.operation", attributes={"test.attr": "value"}) as span:
        assert span is not None
        assert span.is_recording()

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test.operation"
    assert spans[0].attributes is not None
    assert spans[0].attributes.get("test.attr") == "value"


def test_create_span_with_exception() -> None:
    """Test that create_span records exceptions."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar.plugins.opentelemetry import create_span

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    from opentelemetry import trace

    trace._TRACER_PROVIDER = tracer_provider
    trace.set_tracer_provider(tracer_provider)

    with pytest.raises(ValueError, match="Test exception"):
        with create_span("test.failing_operation"):
            raise ValueError("Test exception")

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test.failing_operation"

    # Check for exception event
    exception_events = [event for event in spans[0].events if event.name == "exception"]
    assert exception_events
    first_event = exception_events[0]
    assert first_event.attributes is not None
    assert first_event.attributes.get("exception.type") == "ValueError"
    assert first_event.attributes.get("exception.message") == "Test exception"


def test_cli_instrumentation_creates_span() -> None:
    """CLI commands emit spans when CLI instrumentation is enabled."""

    from click.testing import CliRunner
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar.cli.main import litestar_group
    from litestar.config.app import AppConfig
    from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

    plugin = OpenTelemetryPlugin(OpenTelemetryConfig(tracer_provider=tracer_provider, instrument_cli=True))
    plugin.on_app_init(AppConfig())

    runner = CliRunner()
    result = runner.invoke(litestar_group, ["version"])
    assert result.exit_code == 0

    spans = exporter.get_finished_spans()
    assert any(span.name.startswith("cli.") for span in spans), "expected CLI spans when instrument_cli is enabled"


def test_exception_stacktrace_recorded_in_middleware() -> None:
    """Ensure middleware records stack traces on exceptions."""

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar import get
    from litestar.plugins.opentelemetry import OpenTelemetryConfig
    from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
    from litestar.testing import create_test_client

    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    @get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    with create_test_client(
        route_handlers=[boom],
        plugins=[OpenTelemetryConfig(tracer_provider=tracer_provider).plugin],
    ) as client:
        response = client.get("/boom")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR

    spans = exporter.get_finished_spans()
    # find span with exception event
    exception_spans = [span for span in spans if any(event.name == "exception" for event in span.events)]
    assert exception_spans, "expected exception span"
    stacktrace_attrs = [
        (event.attributes or {}).get("exception.stacktrace")
        for span in exception_spans
        for event in span.events
        if event.name == "exception"
    ]
    assert any(stacktrace_attrs), "stacktrace attribute should be recorded"
    first_stacktrace = next(filter(None, stacktrace_attrs))
    assert "RuntimeError" in str(first_stacktrace)
