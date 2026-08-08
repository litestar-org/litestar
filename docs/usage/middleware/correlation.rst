======================
Correlation Middleware
======================

The correlation middleware extracts, generates, and propagates correlation and trace IDs across asynchronous execution contexts using Python's :mod:`contextvars`.

This facilitates distributed tracing and unified logging across microservices and async handlers.

Features
--------

- Priority header fallback (:code:`x-request-id`, :code:`traceparent`, :code:`x-cloud-trace-context`, etc.).
- W3C :code:`traceparent` defensive parsing.
- UUID4 generation fallback when no header matches.
- ContextVar isolation across concurrent requests.
- Automatic scope state propagation (:code:`scope["state"]["correlation_id"]`).
- Optional response-header propagation.

Standalone Usage
----------------

.. literalinclude:: /examples/middleware/correlation_standalone.py
    :language: python

Correlation Context API
-----------------------

The :class:`~litestar.middleware.correlation.CorrelationContext` utility class provides static accessors:

.. code-block:: python

    from litestar.middleware.correlation import CorrelationContext

    # Retrieve current ID
    correlation_id = CorrelationContext.get()

    # Scope context manager
    with CorrelationContext.context("custom-id"):
        ...

The middleware validates W3C ``traceparent`` values, reads raw ASGI headers, optionally propagates the selected ID in
the response, and restores pre-existing scope state after each request.
