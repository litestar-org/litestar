# Logging Middleware

Starlite ships with a robust logging middleware that allows logging HTTP request and responses while building on
the [app level logging configuration](../../0-the-starlite-app/4-logging.md):

```python
from starlite import Starlite, LoggingConfig, get
from starlite.middleware import LoggingMiddlewareConfig

logging_middleware_config = LoggingMiddlewareConfig()


@get("/")
def my_handler() -> dict[str, str]:
    return {"hello": "world"}


app = Starlite(
    route_handlers=[my_handler],
    logging_config=LoggingConfig(),
    middleware=[logging_middleware_config.middleware],
)
```

The logging middleware use the logger configuration defined on the application level, which allows for using both stdlib
logging or [structlog](https://www.structlog.org/en/stable/index.html), depending on the configuration used (
see [logging](../../0-the-starlite-app/4-logging.md) for more details).

## Obfuscating Logging Output

Sometimes certain data, e.g. request or response headers, needs to be obfuscated. This is supported by the middleware configuration:

```python
from starlite.middleware import LoggingMiddlewareConfig

logging_middleware_config = LoggingMiddlewareConfig(
    request_cookies_to_obfuscate={"my-custom-session-key"},
    response_cookies_to_obfuscate={"my-custom-session-key"},
    request_headers_to_obfuscate={"my-custom-header"},
    response_headers_to_obfuscate={"my-custom-header"},
)
```

The middleware will obfuscate the headers `Authorization` and `X-API-KEY`, and the cookie `session` by default.

You can read more about the configuration options in the [api reference][starlite.middleware.logging.LoggingMiddlewareConfig]
