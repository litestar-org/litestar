Correlation IDs
===============

:class:`~litestar.middleware.correlation.CorrelationMiddleware` reads a
distributed-trace correlation ID from a configurable list of request headers
and propagates it through a :class:`~contextvars.ContextVar` so handlers,
dependencies, and loggers can read it for the duration of a request.

The middleware is a *propagation primitive*: it stores the **entire raw
header value** unchanged. For W3C ``traceparent`` that means the full
``version-trace_id-parent_id-flags`` quadruple — preserving the parent-span
ID and the sample-flag bit so downstream services can forward the value
verbatim. For cloud-vendor headers (AWS, GCP, …) the raw vendor format is
preserved as-is.

When no recognised header is present, the middleware **generates a fresh
W3C-compliant** ``traceparent`` value (``00-<32 hex>-<16 hex>-01``) so that
the contextvar value is always something downstream services can parse.


Header lookup order
-------------------

By default the middleware tries the W3C ``traceparent`` header first, then
the entries of
:data:`~litestar.middleware.correlation.TRACE_CONTEXT_FALLBACK_HEADERS`:

* ``traceparent`` — W3C Trace Context
* ``x-amzn-trace-id`` — AWS X-Ray
* ``x-cloud-trace-context`` — Google Cloud Trace
* ``x-correlation-id`` — generic
* ``x-request-id`` — generic / Kubernetes

The first present header wins. To pick a different primary header, pass
``header=``. To disable the fallback list and only consult the primary
header, pass ``auto_trace_headers=False``. A custom fallback list can be
provided via ``fallback_headers=``.

The resolved header lookup order is computed once at construction time —
not on every request — to keep the per-request hot path to a single header
dict lookup and a contextvar ``set``/``reset`` pair.


Standalone usage
----------------

The middleware lives in ``litestar.middleware`` and has no OpenTelemetry
dependency, so it can be used in any Litestar app:

.. code-block:: python

    from litestar import Litestar, get
    from litestar.middleware.correlation import CorrelationContext, CorrelationMiddleware


    @get("/")
    def index() -> dict[str, str | None]:
        return {"correlation_id": CorrelationContext.get()}


    app = Litestar(route_handlers=[index], middleware=[CorrelationMiddleware()])


Reading the correlation ID
--------------------------

From inside a handler, dependency, or any code running on the request task,
call :meth:`~litestar.middleware.correlation.CorrelationContext.get`:

.. code-block:: python

    from litestar.middleware.correlation import CorrelationContext

    correlation_id = CorrelationContext.get()  # str | None

Outside of a request scope (e.g. during application startup) the call
returns ``None``.

If you need only the 32-character W3C trace ID — for example to attach it
to log records — use the public helper:

.. code-block:: python

    from litestar.middleware.correlation import (
        CorrelationContext,
        trace_id_from_traceparent,
    )

    raw = CorrelationContext.get() or ""
    trace_id = trace_id_from_traceparent(raw)  # str | None


Logging integration
-------------------

Because the value lives in a ``ContextVar``, a tiny logging filter is enough
to inject it into every log record:

.. code-block:: python

    import logging

    from litestar.middleware.correlation import CorrelationContext


    class CorrelationIdFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.correlation_id = CorrelationContext.get() or "-"
            return True


    handler = logging.StreamHandler()
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(correlation_id)s] %(levelname)s %(message)s")
    )

For ``structlog`` users, ``CorrelationContext.get()`` can be wired into a
``contextvars.bind_contextvars`` call or a custom processor.


OpenTelemetry integration
-------------------------

When using the
:class:`~litestar.contrib.opentelemetry.OpenTelemetryPlugin`, set
:attr:`~litestar.contrib.opentelemetry.OpenTelemetryConfig.enable_correlation_middleware`
to ``True`` and the plugin will inject the correlation middleware ahead of
its instrumentation:

.. code-block:: python

    from litestar import Litestar
    from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

    plugin = OpenTelemetryPlugin(
        OpenTelemetryConfig(enable_correlation_middleware=True),
    )
    app = Litestar(route_handlers=[...], plugins=[plugin])

The OpenTelemetry config exposes the same knobs as the middleware
constructor (``correlation_header``, ``correlation_headers``,
``auto_trace_headers``) so you can adjust behaviour without manually
constructing the middleware.


Defensive parsing
-----------------

A malformed ``traceparent`` value (one that fails W3C validation — wrong
length, non-hex characters, the reserved ``ff`` version, or an all-zeros
trace ID or parent ID) is logged at ``DEBUG`` level and stored *as-is*.
The middleware never raises on bad input — request handling proceeds
normally with whatever the client sent.


.. seealso::

    * :class:`~litestar.middleware.correlation.CorrelationMiddleware` — full API
    * :class:`~litestar.middleware.correlation.CorrelationContext`
    * :func:`~litestar.middleware.correlation.trace_id_from_traceparent`
    * :data:`~litestar.middleware.correlation.TRACE_CONTEXT_FALLBACK_HEADERS`
    * :doc:`/usage/metrics/open-telemetry` and the
      :class:`~litestar.contrib.opentelemetry.OpenTelemetryPlugin` for
      span-level integration
