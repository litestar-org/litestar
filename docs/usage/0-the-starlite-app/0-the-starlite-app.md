# The Starlite App

At the root of every Starlite application is an **instance** of the `Starlite` class or a subclass of it. Typically,
this code will be placed in a file called `main.py` at the **project's root directory**.

Creating an app is straightforward – the **only required kwarg is a list**
of [Controllers](../1-routing/3-controllers.md#controllers), [Routers](../1-routing/2-routers.md)
or [Route Handlers](../2-route-handlers/1-http-route-handlers.md):

```python
from starlite import Starlite, get


@get(path="/")
def health_check() -> str:
    return "healthy"


app = Starlite(route_handlers=[health_check])
```

The **app instance is the root level** of the app - it has the base path of "/" and all root level Controllers, Routers
and Route Handlers should be registered on it. See [registering routes](../1-routing/1-registering-routes.md) for
full details.

The Starlite constructor accepts the following additional kwargs:

- `after_request`: A [after request lifecycle hook handler](../13-lifecycle-hooks.md#after-request).
- `after_response`: A [after response lifecycle hook handler](../13-lifecycle-hooks.md#after-response).
- `allowed_hosts`: A list of allowed hosts. If set this enables
  the [AllowedHostsMiddleware](../7-middleware/3-builtin-middlewares/2-allowed-hosts-middleware.md).
- `before_request`: A [before request lifecycle hook handler](../13-lifecycle-hooks.md#before-request).
- `cache_config`: A [CacheConfig instance](../16-caching.md#configuring-caching). Allows specification of cache
  parameters such as backend, expiry, etc.
- `compression_config`:
  A [CompressionConfig instance](../7-middleware/3-builtin-middlewares/4-compression-middleware.md). Built in support
  for Gzip and Brotli compression.
- `cors_config`: An instance of `starlite.config.CORSConfig`. If set this enables
  the [CORSMiddleware](../7-middleware/3-builtin-middlewares/1-cors-middleware.md).
- `debug`: A boolean flag toggling debug mode on and off, if True, 404 errors will be rendered as HTML with a stack
  trace. This option should _not_ be used in production. Defaults to `False`.
- `dependencies`: A dictionary mapping dependency providers.
  See [dependency-injection](../6-dependency-injection/0-dependency-injection-intro.md).
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions.
  See [exception-handlers](../17-exceptions#exception-handling).
- `guards`: A list of guard callable. See [guards](../9-guards.md).
- `middleware`: A list of middlewares. See [middleware](../7-middleware/0-middleware-intro.md).
- `on_shutdown`: A list of callables that are called during the application shutdown.
  See [startup-and-shutdown](./1-startup-and-shutdown.md).
- `on_startup`: A list of callables that are called during the application startup.
  See [startup-and-shutdown](./1-startup-and-shutdown.md).
- `openapi_config`: An instance of `starlite.config.OpenAPIConfig`. Defaults to the baseline config.
  See [open-api](../12-openapi.md).
- `parameters`: A mapping of parameters definition that will be available in all application paths.
  See [layered parameters](../3-parameters/4-layered-parameters.md).
- `response_class`: A custom response class to be used as the app's default.
  See [using-custom-responses](../5-responses/0-responses-intro.md#using-custom-responses).
- `response_cookies`: A list of `Cookie` instances. See [response-cookies](../5-responses/5-response-cookies.md)
- `response_headers`: A dictionary of `ResponseHeader` instances.
  See [response-headers](../5-responses/0-responses-intro.md#response-headers).
- `static_files_config`: An instance or list of `starlite.config.StaticFilesConfig`.
  See [static files](./3-static-files.md).
- `tags`: A list of tags to add to the openapi path definitions for all application paths.
  See [open-api](../12-openapi.md).
