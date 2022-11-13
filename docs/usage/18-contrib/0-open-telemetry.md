# Open Telemetry Instrumentation

Starlite includes optional OpenTelemetry instrumentation that is exported from `starlite.contrib.opentelemtry`. To use
this package, you should first install the required dependencies:

```shell title="as separate packages"
pip install opentelemetry-instrumentation-asgi
```

Or by installing Starlite with the `opentelemetry` extra:

```shell title="as 'extra' dependencies"
pip install starlite[opentelemetry]
```

Once these requirements are satisfied, you can instrument your Starlite application by creating an instance
of [OpenTelemetryConfig][starlite.contrib.opentelemetry.OpenTelemetryConfig] and passing the middleware it creates to
the Starlite constructor:

```python
from starlite import Starlite
from starlite.contrib.opentelemetry import OpenTelemetryConfig

open_telemetry_config = OpenTelemetryConfig()

app = Starlite(route_handlers=[], middleware=[open_telemetry_config.middleware])
```

The above example will work out of the box if you configure a global `tracer_provider` and/or `metric_provider` and an
exporter to use these (see the
[OpenTelemetry Exporter docs](https://opentelemetry.io/docs/instrumentation/python/exporters/) for further details).

You can also pass con figuration to the `OpenTelemetryConfig` telling it which providers to use. Consult
[reference docs][starlite.contrib.opentelemetry.OpenTelemetryConfig] regarding the configuration options you can use.
