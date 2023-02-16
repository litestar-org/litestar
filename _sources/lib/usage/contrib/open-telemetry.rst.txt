Open Telemetry Instrumentation
==============================

Starlite includes optional OpenTelemetry instrumentation that is exported from ``starlite.contrib.opentelemetry``. To use
this package, you should first install the required dependencies:

.. code-block:: bash
    :caption: as separate package

    pip install opentelemetry-instrumentation-asgi


.. code-block:: bash
    :caption: as a Starlite extra

    pip install starlite[opentelemetry]

Once these requirements are satisfied, you can instrument your Starlite application by creating an instance
of :class:`OpenTelemetryConfig <starlite.contrib.opentelemetry.OpenTelemetryConfig>` and passing the middleware it creates to
the Starlite constructor:

.. code-block:: python

   from starlite import Starlite
   from starlite.contrib.opentelemetry import OpenTelemetryConfig

   open_telemetry_config = OpenTelemetryConfig()

   app = Starlite(route_handlers=[], middleware=[open_telemetry_config.middleware])

The above example will work out of the box if you configure a global ``tracer_provider`` and/or ``metric_provider`` and an
exporter to use these (see the
`OpenTelemetry Exporter docs <https://opentelemetry.io/docs/instrumentation/python/exporters/>`_ for further details).

You can also pass con figuration to the ``OpenTelemetryConfig`` telling it which providers to use. Consult
:class:`reference docs <starlite.contrib.opentelemetry.OpenTelemetryConfig>` regarding the configuration options you can use.
