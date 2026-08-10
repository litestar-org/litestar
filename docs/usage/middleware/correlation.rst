======================
Correlation Middleware
======================

The correlation middleware extracts, generates, and propagates correlation and trace IDs for each connection.

This facilitates distributed tracing and unified logging across microservices and async handlers.

Features
--------

- Priority header fallback (:code:`x-request-id`, :code:`x-correlation-id`, and :code:`traceparent` by default).
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
        return get_correlation_id(request)

The helper also accepts a raw ASGI scope or a :class:`~litestar.connection.WebSocket` directly:

.. code-block:: python

    from litestar import WebSocket, websocket


    @websocket("/ws")
    async def websocket_handler(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_text(get_correlation_id(socket) or "missing")

Header behavior
---------------

The middleware validates W3C ``traceparent`` values. Values from all other configured headers are treated as opaque
correlation values. Additional formats, including ``grpc-trace-bin`` and provider-specific headers, can be selected
with ``header_names``; the middleware does not parse those formats.

Incoming scope headers are not modified. By default, the selected correlation ID replaces ``x-request-id`` in the
response; set ``response_header_name=None`` to disable this. This response header contains the selected correlation
value, not a raw copy of the incoming header. The middleware does not propagate correlation headers to outbound
requests.
