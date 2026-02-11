.. _logging-usage:

Logging
=======

You can configure how and what Litestar logs via
:class:`~litestar.logging.config.LoggingConfig`.

.. note::

    This is not a general way to configure logging. For that, refer to :mod:`logging`.
    The logging configuration is specifically for how Litestar logs, and to integrate it
    with an existing logging environment.

.. attention::

    Exceptions won't be logged by default, except in debug mode. Make sure to use ``log_exceptions="always"`` as in the
    example above to log exceptions if you need it.

Controlling exception logging
-----------------------------

While ``log_exceptions`` controls when exceptions are logged, sometimes you may want to suppress stack traces for specific
exception types or HTTP status codes. The ``disable_stack_trace`` parameter allows you to specify a set of exception types
or status codes that should not generate stack traces in logs:

.. code-block:: python

   from litestar import Litestar
   from litestar.logging import LoggingConfig

   # Don't log stack traces for 404 errors and ValueError exceptions
   logging_config = LoggingConfig(
       debug=True,
       disable_stack_trace={404, ValueError},
   )

   app = Litestar(logging_config=logging_config)

This is particularly useful for common exceptions that you expect in normal operation and don't need detailed stack traces for.

Default handlers
----------------

By default, Litestar registers two handlers:

- ``litestar_stream_handler``: A :class:`logging.StreamHandler`
- ``litestar_queue_handler``: A non-blocking :class:`logging.handlers.QueueHandler`,
  outputting to ``litestar_stream_handler``.


Non-blocking logging
++++++++++++++++++++

Since logging is a blocking operation by default, Litestar configures a non-blocking
:class:`logging.handlers.QueueHandler` to use for its own loggers, registered under the
key ``litestar_queue_handler``. It will start automatically with your application, and
shut down at interpreter exit. On application exit, the queue is flushed to ensure all
messages are processed properly. This behaviour can be disabled via the
:attr:`~litestar.logging.config.LoggingConfig.configure_queue_handler` flag.

.. important::

    When setting ``configure_queue_handler=False``, be sure to provide a non-blocking
    alternative handler under ``litestar_stream_handler``


Structlog integration
---------------------

Litestar offers a built-in `structLog <https://www.structlog.org/en/stable/>`
integration, which enables Litestar to use structlog. To set it up, use
:class:`~litestar.logging.structlog.StructLoggingConfig` instead of
:class:`~litestar.logging.config.LoggingConfig`:

.. code-block:: python

   from litestar import Litestar, Request, get
   from litestar.plugins.structlog import StructLoggingConfig

   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("inside a request")
       return None

   app = Litestar(route_handlers=[my_router_handler], logging_config=StructLoggingConfig())


.. note::

    Litestar uses structlog's stdlib logging integration to handle cofiguration and
    ensure non-blocking logging.


.. important::

    Litestar does *not* configure structlog globally via :func:`structlog.configure`.
    Instead, it creates its own logger(s) via :func:`structlog.wrap_logger`


Configuring Litestar's structlogger
+++++++++++++++++++++++++++++++++++

You can pass custom structlog configuration to
:class:`~litestar.logging.structlog.StructLoggingConfig`, which will get passed on to
the wrapped logger:

.. code-block:: python

    from litestar import Litestar, Request, get
    from litestar.plugins.structlog import StructLoggingConfig

    def timestamper(logger, log_method, event_dict):
        event_dict["timestamp"] = calendar.timegm(time.gmtime())
        return event_dict

    config = StructLoggingConfig(processors=[timestamper])


Testing
+++++++

You can use structlog's :func:`structlog.testing.capture_logs` function to capture logs.
By default, Litestar will disable its own processors if it detects that
``capture_logs`` is being used.

.. note::

    Be sure to enable ``capture_logs`` *before* you set up your application, otherwise
    structlog will try to patch the configuration after Litestar has already set up its
    loggers.


Request logging
---------------

You turn on request / response logging by setting
:attr:`~litestar.logging.config.LoggingConfig.log_requests` to ``True``, which will
inject a :class:`~litestar.middleware.logging.LoggingMiddleware`.

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

Configuration
+++++++++++++

Other options can be configured by instantiating the middleware directly:

.. literalinclude:: /examples/middleware/logging_middleware.py
    :language: python


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
