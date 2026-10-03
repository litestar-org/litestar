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
of :class:`OpenTelemetryConfig <litestar.plugins.opentelemetry.OpenTelemetryConfig>` and passing the middleware it creates to
the Litestar constructor:

.. code-block:: python

   from litestar import Litestar
   from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

   open_telemetry_config = OpenTelemetryConfig()

   app = Litestar(plugins=[OpenTelemetryPlugin(open_telemetry_config)])

The above example will work out of the box if you configure a global ``tracer_provider`` and/or ``metric_provider`` and an
exporter to use these (see the
`OpenTelemetry Exporter docs <https://opentelemetry.io/docs/instrumentation/python/exporters/>`_ for further details).

You can also pass configuration to the ``OpenTelemetryConfig`` telling it which providers to use. Consult
:class:`reference docs <litestar.plugins.opentelemetry.OpenTelemetryConfig>` regarding the configuration options you can use.

Viewing traces locally
-----------------------

To see OpenTelemetry in action without setting up an external collector, you can configure a
``TracerProvider`` with the ``ConsoleSpanExporter``, which prints completed spans directly to your
terminal. This is useful for quickly verifying that instrumentation is working correctly.

.. code-block:: python
   :caption: app.py

   from litestar import Litestar, get
   from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

   # Set up a tracer provider that exports spans to the console
   provider = TracerProvider()
   provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
   trace.set_tracer_provider(provider)

   open_telemetry_config = OpenTelemetryConfig()


   @get("/")
   async def index() -> dict[str, str]:
       return {"hello": "world"}


   app = Litestar(route_handlers=[index], plugins=[OpenTelemetryPlugin(open_telemetry_config)])

Run the application and make a request to it:

.. code-block:: bash

   litestar run
   # in another terminal
   curl http://127.0.0.1:8000/

You should see a JSON-formatted span printed to the terminal running the app, containing fields such
as ``name``, ``context``, ``start_time``, ``end_time``, and ``attributes`` describing the request that
was just handled. This confirms your instrumentation is active and gives you a concrete artifact to
inspect before wiring up a real exporter (e.g. OTLP to Jaeger, Tempo, or a vendor backend).

.. note::
    ``SimpleSpanProcessor`` exports each span immediately as it finishes, which is convenient for local
    debugging but not recommended for production — use ``BatchSpanProcessor`` in production for better
    performance, as it batches and exports spans asynchronously.

Does it matter if I use ``litestar run`` or a production server like Granian?
--------------------------------------------------------------------------------

No — instrumentation is applied at the ASGI application/middleware level, before any server process
ever touches it. Whether you run your app with ``litestar run`` (development server), Granian, Uvicorn,
or Hypercorn, the ``OpenTelemetryPlugin`` wraps your app the same way and produces the same spans per
request.

The one thing to be aware of: if you run a production server with multiple worker processes (e.g.
Granian with ``--workers 4``), each worker process gets its own independent ``TracerProvider`` unless you
configure exporting to a shared external collector. This isn't a Litestar-specific concern — it's how
OpenTelemetry SDKs work across any multi-process Python server — but it means the console exporter
example above is best used with a single worker/process for local debugging.
