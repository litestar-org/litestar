OpenTelemetry
=============

Litestar includes optional OpenTelemetry instrumentation that is exported from ``litestar.plugins.opentelemetry``. To use
this package, you should first install the required dependencies:

.. code-block:: bash
    :caption: as separate package

    pip install opentelemetry-instrumentation-asgi


.. code-block:: bash
    :caption: as a Litestar extra

    pip install 'litestar[opentelemetry]'

Once these requirements are satisfied, you can instrument your Litestar application by creating an instance
of :class:`OpenTelemetryConfig <litestar.plugins.opentelemetry.OpenTelemetryConfig>` and passing it to the plugin:

.. code-block:: python

   from litestar import Litestar
   from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

   open_telemetry_config = OpenTelemetryConfig()

   app = Litestar(plugins=[OpenTelemetryPlugin(open_telemetry_config)])

The above example will work out of the box if you configure a global ``tracer_provider`` and/or ``metric_provider`` and an
exporter to use these (see the
`OpenTelemetry Exporter docs <https://opentelemetry.io/docs/instrumentation/python/exporters/>`_ for further details).

You can also pass configuration to the ``OpenTelemetryConfig`` telling it which providers to use. Consult the
:class:`OpenTelemetryConfig <litestar.plugins.opentelemetry.OpenTelemetryConfig>` reference docs for all available configuration options.

Configuration options
---------------------

Provider configuration
~~~~~~~~~~~~~~~~~~~~~~

The following options allow you to configure custom OpenTelemetry providers:

- ``tracer_provider``: Custom ``TracerProvider`` instance. If omitted, the globally configured provider is used.
- ``meter_provider``: Custom ``MeterProvider`` instance. If omitted, the globally configured provider is used.
- ``meter``: Custom ``Meter`` instance. If omitted, the meter from the provider is used.

Example with custom tracer provider:

.. code-block:: python

   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
   from litestar import Litestar
   from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

   # Configure a custom tracer provider
   tracer_provider = TracerProvider()
   tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

   config = OpenTelemetryConfig(tracer_provider=tracer_provider)
   app = Litestar(plugins=[OpenTelemetryPlugin(config)])

Hook handlers
~~~~~~~~~~~~~

Hook handlers allow you to customize span behavior at various points in the request lifecycle:

- ``server_request_hook_handler``: Called with the server span and ASGI scope for every incoming request.
- ``client_request_hook_handler``: Called with the internal span when the ``receive`` method is invoked.
- ``client_response_hook_handler``: Called with the internal span when the ``send`` method is invoked.

Example adding custom attributes:

.. code-block:: python

   from opentelemetry.trace import Span
   from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

   def request_hook(span: Span, scope: dict) -> None:
       span.set_attribute("custom.user_agent", scope.get("headers", {}).get("user-agent", ""))

   config = OpenTelemetryConfig(server_request_hook_handler=request_hook)
   app = Litestar(plugins=[OpenTelemetryPlugin(config)])

URL filtering
~~~~~~~~~~~~~

You can exclude specific URLs from instrumentation:

- ``exclude``: Pattern or list of patterns to exclude from instrumentation.
- ``exclude_opt_key``: Route option key to disable instrumentation on a per-route basis.
- ``exclude_urls_env_key`` (default ``"LITESTAR"``): Environment variable prefix for excluded URLs. With the default, the environment variable ``LITESTAR_EXCLUDED_URLS`` will be checked.

Example excluding health check endpoints:

.. code-block:: python

   from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

   config = OpenTelemetryConfig(
       exclude=["/health", "/readiness", "/metrics"]
   )
   app = Litestar(plugins=[OpenTelemetryPlugin(config)])

Advanced options
~~~~~~~~~~~~~~~~

- ``scope_span_details_extractor``: Callback that returns a tuple of ``(span_name, attributes)`` for customizing span details from the ASGI scope.
- ``scopes``: ASGI scope types to process (e.g., ``{"http", "websocket"}``). If ``None``, both HTTP and WebSocket are processed.
- ``middleware_class``: Custom middleware class. Must be a subclass of ``OpenTelemetryInstrumentationMiddleware``.

Litestar-specific spans
------------------------

Litestar can automatically create spans for framework events. With :class:`OpenTelemetryConfig <litestar.plugins.opentelemetry.OpenTelemetryConfig>`,
all instrumentation options are enabled by default:

- ``instrument_guards`` (default ``True``): Create ``guard.*`` spans for each guard executed within a request.
- ``instrument_events`` (default ``True``): Create ``event.emit.*`` and ``event.listener.*`` spans for the event emitter.
- ``instrument_lifecycle`` (default ``True``): Wrap application startup/shutdown hooks with ``lifecycle.*`` spans.
- ``instrument_cli`` (default ``True``): Emit ``cli.*`` spans for Litestar CLI commands.

Example with selective instrumentation:

.. code-block:: python

   from litestar import Litestar
   from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

   # Enable only guard and event instrumentation
   config = OpenTelemetryConfig(
       instrument_guards=True,
       instrument_events=True,
       instrument_lifecycle=False,
       instrument_cli=False
   )

   app = Litestar(plugins=[OpenTelemetryPlugin(config)])
