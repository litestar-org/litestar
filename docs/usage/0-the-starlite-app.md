# The Starlite app

At the root of every Starlite application is an instance of the `Starlite` class or a subclass of it. Typically, this
code will be placed in a file called `main.py` at the project's source folder root.

Creating an app is straightforward. It only requires a list with a mix of either Controllers, 
Routers, or [route handlers](2-route-handlers.md):

```python title="my_app/main.py"
from starlite import Starlite, get


@get(path="/")
def health_check() -> str:
    return "healthy"


app = Starlite(route_handlers=[health_check])
```

This `app` instance is the root of the application - it has the base path of "/" and all root 
level Controllers, Routers and Route Handlers should be registered on it. 
See [registering routes](1-routers-and-controllers.md#registering-routes) for details.

You can additionally pass the following kwargs to the Starlite constructor:

- `allowed_hosts`: A list of allowed hosts. If set this enables the [AllowedHostsMiddleware](https://starlite-api.github.io/starlite/usage/7-middleware/#trusted-hosts).
- `cors_config`: An instance of `starlite.config.CORSConfig`. If set this enables the [CORSMiddleware](https://starlite-api.github.io/starlite/usage/7-middleware/#cors).
- `debug`: A boolean flag toggling debug mode on and off, if True, 404 errors will be rendered as HTML with a stack
  trace. Beware that enabling this option in production might be a security risk. Defaults to `False`.
- `dependencies`: A dictionary mapping dependency providers. 
  See the section on [dependency injection](6-dependency-injection.md) for details.
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions.
  See the section on [exception handlers](#exception-handling) for details.
- `guards`: A list of callables. 
  See the section on [guards](9-guards.md) for details.
- `middleware`: A list of classes adhering to the Starlite `MiddlewareProtocol`, instance of the Starlette `Middleware`
  class, or subclasses of the Starlette `BaseHTTPMiddleware` class. 
  See the [middleware](7-middleware.md) section for details.
- `on_shutdown`: A list of callables that are called during the application shutdown. 
  See the [lifecycle](#lifecycle) section for details.
- `on_startup`: A list of callables that are called during the application startup. 
  See the [lifecycle](#lifecycle) section for details.
- `openapi_config`: An instance of `starlite.config.OpenAPIConfig`. Defaults to the baseline config.
  See the [OpenAPI](10-openapi.md) section for details.
- `redirect_slashes`: A boolean flag dictating whether to redirect urls ending with a trailing slash to urls without a
  trailing slash if no match is found. Defaults to `True`.
- `response_class`: A custom response class to be used as the app default.
  See the [using custom responses](5-responses.md#using-custom-responses) section for details.
- `response_headers`: A dictionary of `ResponseHeader` instances.
  See the [response headers](5-responses.md#response-headers) section for details.

## Lifecycle

Starlette supports two kinds of application lifecycle management - `on_startup`
/ `on_shutdown` hooks, which accept a sequence of callables, and `lifespan`, which accepts an `AsyncContextManager`. To
simplify matters, Starlite only supports the `on_startup` / `on_shutdown` hooks. To use these you can pass a **list** of
callables, what's called "event handlers" in Starlette, which will be called during the application startup or shutdown.
These callables can be either sync or async - methods or functions.

A classic use case for this is database connectivity. Often you will want to establish the connection once - on
application startup, and then close the connection on shutdown. For example, lets assume we create a connection to a
Postgres DB using the async engine from [SQLAlchemy](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html), and
we therefore opt to create two functions, one to get or create the connection, and another to close it:

```python title="my_app/postgres.py"
from os import environ
from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from starlette.datastructures import State

state = State()


def get_postgres_connection() -> AsyncEngine:
    """Returns the Postgres connection. If it doesn't exist, creates it and saves it in a State object"""
    postgres_connection_string = environ.get("POSTGRES_CONNECTION_STRING")
    if not postgres_connection_string:
        raise ValueError("Missing ENV Variable POSTGRES_CONNECTION_STRING")
    if not state.get("postgres_connection"):
        state["postgres_connection"] = create_async_engine(postgres_connection_string)
    return cast(AsyncEngine, state["postgres_connection"])


async def close_postgres_connection():
    """Closes the postgres connection stored in the given State object"""
    if state.get("postgres_connection"):
        await cast(AsyncEngine, state["postgres_connection"]).dispose()
```

We now simply need to pass these to the Starlite `__init__` method to ensure these are called correctly:

```python title="my_app/main.py"
from my_app.postgres import get_postgres_connection, close_postgres_connection

from starlite import Starlite

app = Starlite(on_startup=[get_postgres_connection], on_shutdown=[close_postgres_connection])
```

## Logging

Another thing most applications will need to set up as part of startup is logging. 
Although Starlite does not configure logging for you, it does come with a convenience `pydantic` 
model called `LoggingConfig`, which you can use like so:

```python title="my_app/main.py"
from starlite import Starlite, LoggingConfig

my_app_logging_config = LoggingConfig(
    loggers={
        "my_app": {
            "level": "INFO",
            "handlers": ["console"],
        }
    }
)

app = Starlite(on_startup=[my_app_logging_config.configure])
```

`LoggingConfig` is merely a convenience wrapper around the standard library's _DictConfig_ options, which can be rather
confusing.

In the example above, we define a logger for the "my_app" namespace with a log-level of "INFO".
The handler will log messages of severity `INFO` or above. By default, the `LoggingConfig` class logs to `sys.stdout`.

You don't need to use `LoggingConfig` to set up logging. This is completely decoupled from Starlite itself, and you are
free to use whatever solution you want for this (e.g. [loguru](https://github.com/Delgan/loguru)). 
If you do set up logging - then the `on_startup` hook is a good place to do this.

## Exceptions

The Starlite `HTTPException` class receives 3 optional kwargs:

* `detail`: The error message. Defaults to the "phrase" of the status code using `http.HttpStatus`.
* `status_code`: A valid HTTP error status code (4xx or 5xx range). Defaults to 500.
* `extra`: A dictionary of arbitrary values. This dictionary will be serialized and sent as part of the response.
  Defaults to `None`.

Starlite has several pre-configured exception subclasses with pre-set error codes that you can use:

* `ImproperlyConfiguredException`: status code 500. Used internally for configuration errors.
* `ValidationException`: status code 400. This is the exception raised when validation or parsing fails.
* `NotFoundException`: status code 404.
* `NotAuthorizedException`: status code 401.
* `PermissionDeniedException`: status code 403.
* `InternalServerException`: status code 500.
* `ServiceUnavailableException`: status code 503.

## Exception Handling

By default, Starlite catches and transforms all unhandled errors into JSON responses. 
If the errors are instances of either the `starlette.exceptions.HTTPException` or the 
`starlite.exceptions.HTTPException`, the responses will include the appropriate status_code. 
Otherwise, the responses will default to 500 - "Internal Server Error".

You can customize exception handling by passing a dictionary mapping either error codes or exception classes to
callables. For example, if you would like to replace the default exception handler with a handler that returns
plain-text responses you could do this:

```python
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from starlite import HTTPException, MediaType, Request, Response, Starlite


def plain_text_exception_handler(_: Request, exc: Exception) -> Response:
    """Default handler for exceptions subclassed from HTTPException"""
    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    detail = ""
    if hasattr(exc, "detail"):
        detail = exc.detail
    if hasattr(exc, "status_code"):
        status_code = exc.status_code
    return Response(
        media_type=MediaType.TEXT,
        content=detail,
        status_code=status_code,
    )


app = Starlite(
    route_handlers=[...],
    exception_handlers={HTTPException: plain_text_exception_handler},
)
```
