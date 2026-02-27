.. _logging-usage:

Request logging
================

Litestar can be configured to log information about requests / responses, via
:class:`~litestar.middleware.logging.LoggingMiddleware`. In that, it is agnostic about
the logging set up, or which logging library is used. You can pass in any object that
conforms to the :class:`logging.Logger` interface, or a callable that returns such a
logger.

.. literalinclude:: /examples/middleware/logging_middleware.py
    :language: python


Default request log properties
++++++++++++++++++++++++++++++

-  ``path``
-  :attr:`~litestar.connection.Request.method`
-  :attr:`~litestar.connection.Request.content_type`
-  :attr:`~litestar.connection.ASGIConnection.query_params`
-  :attr:`~litestar.connection.ASGIConnection.path_params`

Default response log properties
+++++++++++++++++++++++++++++++

- ``status_code``


Obfuscating Logging Output
+++++++++++++++++++++++++++

Sometimes certain data, e.g. request or response headers, needs to be obfuscated:

.. code-block:: python

   from litestar.middleware.logging import LoggingMiddleware

   logging_middleware_config = LoggingMiddleware(
       request_cookies_to_obfuscate={"my-custom-session-key"},
       response_cookies_to_obfuscate={"my-custom-session-key"},
       request_headers_to_obfuscate={"my-custom-header"},
       response_headers_to_obfuscate={"my-custom-header"},
   )

.. note::
    The middleware will obfuscate the headers ``Authorization`` and ``X-API-KEY`` , and
    the cookie ``session`` by default.


Compression and Logging of Response Body
++++++++++++++++++++++++++++++++++++++++

If both :class:`~litestar.config.compression.CompressionConfig` and
:class:`~litestar.middleware.logging.LoggingMiddleware` have been defined for the application, the response
body will be omitted from response logging if it has been compressed, even if ``"body"`` has been included in
:paramref:`~litestar.middleware.logging.LoggingMiddleware.response_log_fields`. To force the body of
compressed responses to be logged, set
:paramref:`~litestar.middleware.logging.LoggingMiddleware.include_compressed_body` to ``True`` , in
addition to including ``"body"`` in ``response_log_fields``.


Structured logging
+++++++++++++++++++

The middleware can be configured to log information in a structured way, by setting
``log_structured=True``. In this mode, Litestar will expect a logger that accept
arbitrary data as keyword arguments.


Integration with third party logging libraries
++++++++++++++++++++++++++++++++++++++++++++++

To integrate with a third party logging library, simply pass in the logger directly:

.. literalinclude:: /examples/middleware/logging_middleware_structlog.py
    :language: python
