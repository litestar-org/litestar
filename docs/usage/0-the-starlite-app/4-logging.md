# Logging

## Standard logging configuration

Logging is a common requirement for web applications that can prove annoying to configure correctly. Although Starlite
does not configure logging out-of-the box, it does come with a convenience `pydantic` model called `LoggingConfig`,
which makes configuring
logging a breeze. It is a convenience wrapper around the standard library's logging _DictConfig_ that pre-configures
logging
to use the `QueueHandler`, which is non-blocking handler that doesn't hurt the performance of async applications.

For example, below we define a logger for the `my_app` namespace to have a level of `INFO` and use the `queue_listener`
the `LoggingConfig` creates. We then pass this to the `on_startup` hook:

```python
from starlite import Starlite, LoggingConfig

my_app_logging_config = LoggingConfig(
    loggers={
        "my_app": {
            "level": "INFO",
            "handlers": ["queue_listener"],
        }
    }
)

app = Starlite(on_startup=[my_app_logging_config.configure])
```

!!! note
    You do not need to use `LoggingConfig` to set up logging. This is completely decoupled from Starlite itself, and
    you are **free to use whatever solution** you want for this (e.g. [loguru](https://github.com/Delgan/loguru)).
    Still, if you do set up logging - then the on_startup hook is a good place to do this.

## Picologging integration

[Picologging](https://github.com/microsoft/picologging) is a high performance logging library that is developed by
Microsoft. Starlite can be easily configured to use this logging library by specifying the picologging classes within
the `LoggingConfig`.

Picologging is designed to be a drop in replacement to the standard logger, and the above example can be implemented by
setting the StreamHandler and QueueListenerHandler class in the `LoggingConfig` as follows:

```python
from starlite import Starlite, LoggingConfig

my_app_logging_config = LoggingConfig(
    handlers={
        "console": {
            "class": "picologging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
        },
        "queue_listener": {
            "class": "starlite.logging.picologging.QueueListenerHandler",
            "handlers": ["cfg://handlers.console"],
        },
    },
    loggers={
        "my_app": {
            "level": "INFO",
            "handlers": ["queue_listener"],
        }
    },
)

app = Starlite(on_startup=[my_app_logging_config.configure])
```
