# Logging Middleware

Starlite includes a simple [LoggingMiddleware][starlite.config.logging.LoggingMiddleware] which log incoming requests
and outgoing responses. It uses default python Logging library but it can be easily replaced by any third part library.

It is not activated by default, you need to add it in the router middlewares.

```python
import json
from starlite import Starlite, Request, get
from starlite.config.logging import LoggingConfig


@get("/")
def my_handler(request: Request) -> None:
    return json.dumps({"hello": "world"})


app = Starlite(route_handlers=[my_handler], middleware=[LoggingConfig().middleware])
```

The middleware has configuration options:

* middleware_logger_name (str): set a specific name to the logger, default is `starlite.middleware.logging`
* middleware_log_request (bool): either log or not incoming request, default is `True`
* middleware_log_response (bool): either log or not outgoing response, default is `True`
* middleware_class (Type[LoggingMiddleware]): define the middleware to use for logging request and response, default is `LoggingMiddleware`. It is handy to override the middleware without changing configuration class.

For instance, you can disable incoming log and change logger name:

```python
import json
from starlite import Starlite, Request, get
from starlite.config.logging import LoggingConfig


@get("/")
def my_handler(request: Request) -> None:
    return json.dumps({"hello": "world"})


config = LoggingConfig(
    middleware_log_request=False, middleware_logger_name="logging_middleware"
)


app = Starlite(route_handlers=[my_handler], middleware=[config.middleware])
```

Default logging produce following line: `www.yourserver.com:80 - GET /entry/point HTTPS/1.1 200` (for response, for
request the status code is replaced by 'incoming'). You can easily change what is logged by making your own middleware.

```python
import json
from starlite import Starlite, Request, get
from starlite.config.logging import LoggingConfig, LoggingMiddleware
from starlette.types import Message, Scope


@get("/")
def my_handler(request: Request) -> None:
    return json.dumps({"hello": "world"})


class MyUbberLogger(LoggingMiddleware):
    def log_request(self, request: "Request", scope: "Scope") -> None:
        """disable logging incoming request"""
        pass

    def log_response(self, request: "Request", message: "Message") -> None:
        """Shorten response log"""
        log_msg = "[{METHOD}]{ENTRY_POINT}:{STATUS}".format(
            METHOD=request.method.upper(),
            ENTRY_POINT=request.base_url.path,
            STATUS=message.get("status", "notset"),
        )
        self.logger.info(log_msg)


config = LoggingConfig(middleware_class=MyUbberLogger)


app = Starlite(route_handlers=[my_handler], middleware=[config.middleware])
```

You can also use a third party for logging. Below an example with PicoLogging.

```python
import json

import picologging
from starlite import Starlite, Request, get
from starlite.config.logging import LoggingConfig, LoggingMiddleware


@get("/")
def my_handler(request: Request) -> None:
    return json.dumps({"hello": "world"})


class PicologgingMiddleware(LoggingMiddleware):
    def get_logger(self) -> picologging.Logger:
        """Get logger from PicoLogging library"""
        return picologging.getLogger(self.config.middleware_logger_name)


config = LoggingConfig(middleware_class=PicologgingMiddleware)


app = Starlite(route_handlers=[my_handler], middleware=[config.middleware])
```
