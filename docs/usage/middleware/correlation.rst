======================
Correlation Middleware
======================

The correlation middleware extracts, generates, and propagates correlation and trace IDs for each connection.

This facilitates distributed tracing and unified logging across microservices and async handlers.

Features
--------

- Priority header fallback (:code:`x-request-id`, :code:`traceparent`, :code:`x-cloud-trace-context`, etc.).
- W3C :code:`traceparent` defensive parsing.
- UUID4 generation fallback when no header matches.
- The active ID is stored on the connection scope, making it available to handlers and other middlewares.
- Optional response-header propagation.

Usage
-----

.. literalinclude:: /examples/middleware/correlation_standalone.py
    :language: python

Accessing the correlation ID
----------------------------

The active correlation ID is stored on the connection scope and can be retrieved anywhere the scope is available -
in handlers, dependencies, or other middlewares - using
:func:`~litestar.middleware.correlation.get_correlation_id`:

.. code-block:: python

    from litestar import Request, get
    from litestar.middleware.correlation import get_correlation_id


    @get("/")
    async def handler(request: Request) -> str | None:
        return get_correlation_id(request.scope)

The middleware validates W3C ``traceparent`` values and optionally propagates the selected ID in the response.
