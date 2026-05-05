from __future__ import annotations

import asyncio
import re
import time
from typing import TYPE_CHECKING, Any, cast

import pytest

from litestar import get
from litestar.middleware.correlation import (
    TRACE_CONTEXT_FALLBACK_HEADERS,
    CorrelationContext,
    CorrelationMiddleware,
    _generate_w3c_traceparent,
    _is_valid_traceparent,
    trace_id_from_traceparent,
)
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_async_test_client, create_test_client

if TYPE_CHECKING:
    from collections.abc import Iterator

    from litestar.handlers import HTTPRouteHandler
    from litestar.types.asgi_types import Receive, Scope, Send


VALID_TRACEPARENT = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
"""Canonical W3C Trace Context example (https://www.w3.org/TR/trace-context/#examples-of-http-traceparent-headers)."""

W3C_TRACEPARENT_RE = re.compile(r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")
"""Pattern for a valid W3C ``traceparent`` value generated as a fallback."""


@pytest.fixture
def correlation_handler() -> Iterator[HTTPRouteHandler]:
    @get("/")
    def handler() -> dict[str, str | None]:
        return {"id": CorrelationContext.get()}

    yield handler


def test_traceparent_is_stored_whole(correlation_handler: HTTPRouteHandler) -> None:
    """Valid traceparent must be stored verbatim so downstream services can propagate it intact."""
    with create_test_client(route_handlers=[correlation_handler], middleware=[CorrelationMiddleware()]) as client:
        response = client.get("/", headers={"traceparent": VALID_TRACEPARENT})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"id": VALID_TRACEPARENT}


def test_malformed_traceparent_falls_back_to_raw(correlation_handler: HTTPRouteHandler) -> None:
    """A traceparent that fails W3C validation is stored as-is — never raises."""
    with create_test_client(route_handlers=[correlation_handler], middleware=[CorrelationMiddleware()]) as client:
        response = client.get("/", headers={"traceparent": "garbage"})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"id": "garbage"}


def test_fallback_value_is_w3c_compliant_traceparent(correlation_handler: HTTPRouteHandler) -> None:
    """When no header matches, the generated fallback must be a valid W3C traceparent.

    A bare UUID hex would break downstream services that parse the value as a
    traceparent — they need the version + trace-id + parent-id + flags shape.
    """
    with create_test_client(route_handlers=[correlation_handler], middleware=[CorrelationMiddleware()]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        value = response.json()["id"]
        assert isinstance(value, str)
        assert W3C_TRACEPARENT_RE.fullmatch(value), value
        # And the generated value must round-trip through the validator.
        assert _is_valid_traceparent(value)


@pytest.mark.parametrize(
    "header",
    [
        ("x-amzn-trace-id", "Root=1-5759e988-bd862e3fe1be46a994272793"),
        ("x-cloud-trace-context", "105445aa7843bc8bf206b12000100000/0;o=1"),
        ("x-correlation-id", "abc-123"),
        ("x-request-id", "req-xyz-789"),
    ],
)
def test_each_fallback_header_is_picked_up(correlation_handler: HTTPRouteHandler, header: tuple[str, str]) -> None:
    name, value = header
    with create_test_client(route_handlers=[correlation_handler], middleware=[CorrelationMiddleware()]) as client:
        response = client.get("/", headers={name: value})
        assert response.json() == {"id": value}


def test_primary_header_wins_over_fallback(correlation_handler: HTTPRouteHandler) -> None:
    with create_test_client(route_handlers=[correlation_handler], middleware=[CorrelationMiddleware()]) as client:
        response = client.get(
            "/",
            headers={"traceparent": VALID_TRACEPARENT, "x-request-id": "should-not-win"},
        )
        assert response.json() == {"id": VALID_TRACEPARENT}


def test_auto_trace_headers_disabled_skips_fallbacks(correlation_handler: HTTPRouteHandler) -> None:
    with create_test_client(
        route_handlers=[correlation_handler],
        middleware=[CorrelationMiddleware(auto_trace_headers=False)],
    ) as client:
        response = client.get("/", headers={"x-request-id": "ignored"})
        # No traceparent and fallbacks disabled → generated W3C traceparent.
        assert W3C_TRACEPARENT_RE.fullmatch(response.json()["id"])


def test_custom_primary_header(correlation_handler: HTTPRouteHandler) -> None:
    with create_test_client(
        route_handlers=[correlation_handler],
        middleware=[CorrelationMiddleware(header="X-Custom-Trace")],
    ) as client:
        response = client.get("/", headers={"x-custom-trace": "custom-value"})
        assert response.json() == {"id": "custom-value"}


def test_token_reset_between_sequential_requests(correlation_handler: HTTPRouteHandler) -> None:
    with create_test_client(route_handlers=[correlation_handler], middleware=[CorrelationMiddleware()]) as client:
        first = client.get("/", headers={"x-request-id": "first"}).json()["id"]
        second = client.get("/", headers={"x-request-id": "second"}).json()["id"]
        third = client.get("/").json()["id"]  # no header → generated W3C traceparent
        assert first == "first"
        assert second == "second"
        assert W3C_TRACEPARENT_RE.fullmatch(third)


async def test_concurrent_requests_are_isolated() -> None:
    @get("/")
    async def handler(req_id: str) -> dict[str, str | None]:
        # Force a context switch to give parallel requests a chance to clobber state if isolation is broken.
        await asyncio.sleep(0)
        return {"sent": req_id, "seen": CorrelationContext.get()}

    async with create_async_test_client(route_handlers=[handler], middleware=[CorrelationMiddleware()]) as client:
        ids = [f"req-{i}" for i in range(50)]
        responses = await asyncio.gather(
            *(client.get("/", params={"req_id": rid}, headers={"x-request-id": rid}) for rid in ids)
        )
        for rid, response in zip(ids, responses):
            assert response.status_code == HTTP_200_OK
            payload = response.json()
            assert payload["sent"] == rid
            assert payload["seen"] == rid


def test_correlation_context_get_returns_none_outside_request() -> None:
    assert CorrelationContext.get() is None


def test_correlation_context_set_and_reset_round_trip() -> None:
    assert CorrelationContext.get() is None
    token = CorrelationContext.set("abc")
    try:
        assert CorrelationContext.get() == "abc"
    finally:
        CorrelationContext.reset(token)
    assert CorrelationContext.get() is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (VALID_TRACEPARENT, True),
        ("00-" + "a" * 32 + "-" + "b" * 16 + "-01", True),
        ("garbage", False),
        ("", False),
        ("00-tooshort-b7ad6b7169203331-01", False),
        ("00-" + "a" * 32 + "-" + "b" * 16, False),  # missing flags
        ("00-" + "a" * 32 + "-" + "b" * 16 + "-01-extra", False),
        ("zz-" + "a" * 32 + "-" + "b" * 16 + "-01", False),  # non-hex version
        ("00-" + "0" * 32 + "-" + "b" * 16 + "-01", False),  # all-zero trace id
        ("00-" + "a" * 32 + "-" + "0" * 16 + "-01", False),  # all-zero parent id
        ("ff-" + "a" * 32 + "-" + "b" * 16 + "-01", False),  # version "ff" reserved as invalid (W3C 3.2.1)
        ("FF-" + "a" * 32 + "-" + "b" * 16 + "-01", False),  # case-insensitive ff rejection
    ],
)
def test_is_valid_traceparent(value: str, expected: bool) -> None:
    assert _is_valid_traceparent(value) is expected


def test_trace_id_from_traceparent_extracts_trace_id() -> None:
    assert trace_id_from_traceparent(VALID_TRACEPARENT) == "0af7651916cd43dd8448eb211c80319c"


def test_trace_id_from_traceparent_returns_none_for_invalid() -> None:
    assert trace_id_from_traceparent("garbage") is None
    assert trace_id_from_traceparent("") is None
    # ``ff`` version is invalid per W3C even though it parses as hex, so the
    # extractor should return ``None`` rather than the trace-id chunk.
    assert trace_id_from_traceparent("ff-" + "a" * 32 + "-" + "b" * 16 + "-01") is None


def test_generated_w3c_traceparent_is_valid() -> None:
    """Generated fallback values must round-trip through the validator."""
    for _ in range(100):
        generated = _generate_w3c_traceparent()
        assert W3C_TRACEPARENT_RE.fullmatch(generated), generated
        assert _is_valid_traceparent(generated), generated


def test_resolved_headers_are_precomputed_at_construction() -> None:
    """ASGI middleware runs per-request — resolution must happen once in __init__."""
    middleware = CorrelationMiddleware()
    # Snapshot. Mutating the public attributes after construction must NOT
    # change the order used at request time, proving the list is precomputed.
    snapshot = middleware._resolved_headers
    assert isinstance(snapshot, tuple)
    middleware.fallback_headers = ("x-completely-different",)
    middleware.header = "x-also-different"
    assert middleware._resolved_headers is snapshot

    # Single-header mode dedupes correctly too.
    only = CorrelationMiddleware(auto_trace_headers=False)
    assert only._resolved_headers == ("traceparent",)


def test_fallback_header_list_contents() -> None:
    """Lock the public default header list — changes here are user-visible."""
    assert TRACE_CONTEXT_FALLBACK_HEADERS == (
        "traceparent",
        "x-amzn-trace-id",
        "x-cloud-trace-context",
        "x-correlation-id",
        "x-request-id",
    )


def test_standalone_without_opentelemetry(correlation_handler: HTTPRouteHandler) -> None:
    """Middleware works with no OTEL plugin, no OTEL imports, plain Litestar app."""
    with create_test_client(route_handlers=[correlation_handler], middleware=[CorrelationMiddleware()]) as client:
        response = client.get("/", headers={"traceparent": VALID_TRACEPARENT})
        assert response.json() == {"id": VALID_TRACEPARENT}


# ---------------------------------------------------------------------------
# OpenTelemetry plugin auto-injection
# ---------------------------------------------------------------------------


def test_otel_plugin_injects_correlation_middleware_when_enabled() -> None:
    from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

    @get("/")
    def handler() -> dict[str, str | None]:
        return {"id": CorrelationContext.get()}

    plugin = OpenTelemetryPlugin(OpenTelemetryConfig(enable_correlation_middleware=True))
    with create_test_client(route_handlers=[handler], plugins=[plugin]) as client:
        response = client.get("/", headers={"traceparent": VALID_TRACEPARENT})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"id": VALID_TRACEPARENT}


def test_otel_plugin_does_not_inject_correlation_middleware_when_disabled() -> None:
    from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

    @get("/")
    def handler() -> dict[str, str | None]:
        return {"id": CorrelationContext.get()}

    plugin = OpenTelemetryPlugin(OpenTelemetryConfig())  # default: disabled
    with create_test_client(route_handlers=[handler], plugins=[plugin]) as client:
        response = client.get("/", headers={"traceparent": VALID_TRACEPARENT})
        # Without the middleware the contextvar is never set
        assert response.json() == {"id": None}


def test_otel_instrumentation_and_correlation_run_together() -> None:
    """Coexistence: OTel must still emit spans AND the correlation contextvar must be set.

    OTel is wrapped at the asgi-handler level by ``Litestar._create_asgi_handler``
    (``app.py`` looks up the plugin and wraps via ``otel_plugin.middleware(app=...)``),
    while the correlation middleware is injected at index 0 of
    ``app_config.middleware`` by ``OpenTelemetryPlugin.on_app_init``. This test
    proves both run in the same request — a regression that disabled OTel via
    the plugin's middleware-pop logic would surface here.
    """
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider(resource=Resource(attributes={SERVICE_NAME: "litestar-correlation-test"}))
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    seen_correlation: list[str | None] = []

    @get("/")
    def handler() -> dict[str, str | None]:
        seen_correlation.append(CorrelationContext.get())
        return {"id": CorrelationContext.get()}

    plugin = OpenTelemetryPlugin(
        OpenTelemetryConfig(tracer_provider=tracer_provider, enable_correlation_middleware=True)
    )
    with create_test_client(route_handlers=[handler], plugins=[plugin]) as client:
        response = client.get("/", headers={"traceparent": VALID_TRACEPARENT})

    assert response.status_code == HTTP_200_OK
    assert response.json() == {"id": VALID_TRACEPARENT}
    # The correlation contextvar was set during the handler (proves the
    # middleware ran).
    assert seen_correlation == [VALID_TRACEPARENT]
    # And OTel emitted at least one span (proves the OTel wrap survived
    # ``on_app_init``'s middleware-list manipulation).
    spans = exporter.get_finished_spans()
    assert spans, "expected at least one OTel span to be exported"


# ---------------------------------------------------------------------------
# Performance smoke
# ---------------------------------------------------------------------------


async def test_middleware_overhead_is_bounded() -> None:
    """Smoke check that the middleware's per-request overhead is small.

    The hot path is a single dict lookup over a precomputed header list and a
    contextvar set/reset. We bench at the ASGI layer (skipping TestClient
    entirely so the measurement isolates the middleware's own work) and assert
    the *per-call* overhead stays well under 100µs. That's far looser than the
    issue's <5% target measured against a real handler, but tight enough to
    catch a catastrophic regression — e.g. someone reintroducing an O(N)
    header rebuild inside ``handle``.
    """
    iterations = 10_000

    async def noop_app(scope: Scope, receive: Receive, send: Send) -> None:  # pragma: no cover - trivial
        return None

    middleware = CorrelationMiddleware()
    wrapped = middleware(noop_app)

    # Bench stubs — minimal scope and never-invoked receive/send. These don't
    # need to be a fully populated ``HTTPScope``/``Receive``/``Send`` since the
    # middleware only reads the headers, sets the context, and forwards.
    async def _receive() -> Any:  # pragma: no cover - never awaited
        return {"type": "http.request", "body": b"", "more_body": False}

    async def _send(message: Any) -> None:  # pragma: no cover - never invoked
        return None

    scope = cast(
        "Scope",
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"traceparent", VALID_TRACEPARENT.encode("latin-1"))],
            "query_string": b"",
        },
    )
    receive = cast("Receive", _receive)
    send = cast("Send", _send)

    # Warm up so import-time / first-call costs don't pollute the bench.
    for _ in range(200):
        await wrapped(scope, receive, send)

    start = time.perf_counter()
    for _ in range(iterations):
        await wrapped(scope, receive, send)
    middleware_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(iterations):
        await noop_app(scope, receive, send)
    baseline_elapsed = time.perf_counter() - start

    overhead_per_call = max(0.0, (middleware_elapsed - baseline_elapsed) / iterations)
    # Generous threshold leaves CI noise headroom while catching anything pathological.
    assert overhead_per_call < 100e-6, (
        f"correlation middleware overhead too high: {overhead_per_call * 1e6:.1f}µs/call "
        f"(middleware {middleware_elapsed:.3f}s vs baseline {baseline_elapsed:.3f}s "
        f"over {iterations} iterations)"
    )
