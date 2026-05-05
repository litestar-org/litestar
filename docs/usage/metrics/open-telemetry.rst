OpenTelemetry
=============

Litestar includes optional OpenTelemetry instrumentation that is exported from ``litestar.contrib.opentelemetry``. To use
this package, you should first install the required dependencies:

.. code-block:: bash
    :caption: as separate package

    pip install opentelemetry-instrumentation-asgi


.. code-block:: bash
    :caption: as a Litestar extra

    pip install 'litestar[opentelemetry]'

Once these requirements are satisfied, you can instrument your Litestar application by creating an instance
of :class:`OpenTelemetryConfig <litestar.contrib.opentelemetry.OpenTelemetryConfig>` and passing the middleware it creates to
the Litestar constructor:

.. code-block:: python

   from litestar import Litestar
   from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

   open_telemetry_config = OpenTelemetryConfig()

   app = Litestar(plugins=[OpenTelemetryPlugin(open_telemetry_config)])

The above example will work out of the box if you configure a global ``tracer_provider`` and/or ``metric_provider`` and an
exporter to use these (see the
`OpenTelemetry Exporter docs <https://opentelemetry.io/docs/instrumentation/python/exporters/>`_ for further details).

You can also pass con figuration to the ``OpenTelemetryConfig`` telling it which providers to use. Consult
:class:`reference docs <litestar.contrib.opentelemetry.OpenTelemetryConfig>` regarding the configuration options you can use.

Trace context correlation
-------------------------

Set
:attr:`OpenTelemetryConfig.enable_correlation_middleware <litestar.contrib.opentelemetry.OpenTelemetryConfig.enable_correlation_middleware>`
to ``True`` and the plugin will inject
:class:`~litestar.middleware.correlation.CorrelationMiddleware` ahead of its
instrumentation. The middleware reads a W3C ``traceparent`` (or one of a
configurable list of cloud-vendor / generic fallback headers) and exposes
the value to handlers and loggers via
:class:`~litestar.middleware.correlation.CorrelationContext`. It works
standalone as well — see
:doc:`/usage/middleware/correlation` for usage patterns, the logging-filter
recipe, and the full configuration surface.
