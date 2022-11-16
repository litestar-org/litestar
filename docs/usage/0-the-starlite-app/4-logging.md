# Logging

Starlite has builtin pydantic based logging configuration that allows users to easily define logging:

```python
from starlite import Starlite, LoggingConfig, Request, get


@get("/")
def my_router_handler(request: Request) -> None:
    request.logger.info("inside a request")
    return None


logging_config = LoggingConfig(
    loggers={
        "my_app": {
            "level": "INFO",
            "handlers": ["queue_listener"],
        }
    }
)

app = Starlite(route_handlers=[my_router_handler], logging_config=logging_config)
```

!!! important
    Starlite configures a non-blocking `QueueListenerHandler` which
    is keyed as `queue_listener` in the logging configuration. The above example is using this handler,
    which is optimal for async applications. Make sure to use it in your own loggers as in the above example.

## Using Picologging

[Picologging](https://github.com/microsoft/picologging) is a high performance logging library that is developed by
Microsoft. Starlite will default to using this library automatically if its installed - requiring zero configuration on
the part of the user. That is, if `picologging` is present the previous example will work with it automatically.

## Using StructLog

[StructLog](https://www.structlog.org/en/stable/) is a powerful structured-logging library. Starlite ships with a dedicated
logging config for using it:

```python
from starlite import Starlite, StructLoggingConfig, Request, get


@get("/")
def my_router_handler(request: Request) -> None:
    request.logger.log("inside a request")
    return None


logging_config = StructLoggingConfig()

app = Starlite(route_handlers=[my_router_handler], logging_config=logging_config)
```

## Subclass Logging Configs

You can easily create you own `LoggingConfig` class by subclassing
[`BaseLoggingConfig`][starlite.config.logging.BaseLoggingConfig] and
implementing the `configure` method.
