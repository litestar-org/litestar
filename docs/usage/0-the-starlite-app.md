# The Starlite App

At the root of every Starlite application is an **instance** of the `Starlite` class or a subclass of it. Typically, this
code will be placed in a file called `main.py` at the **project's root directory**.

Creating an app is straightforward – the **only required kwarg is a list** of [Controllers](1-routers-and-controllers.md#controllers), [Routers](1-routers-and-controllers.md#routers)
or [Route Handlers](2-route-handlers/1_http_route_handlers.md):

```python title="my_app/main.py"
from starlite import Starlite, get


@get(path="/")
def health_check() -> str:
    return "healthy"


app = Starlite(route_handlers=[health_check])
```

The **app instance is the root level** of the app - it has the base path of "/" and all root level Controllers, Routers and
Route Handlers should be registered on it. See [registering routes](1-routers-and-controllers.md#registering-routes) for
full details.

You **can additionally pass** the following **kwargs** to the Starlite constructor:

- `allowed_hosts`: A list of allowed hosts. If set this enables the `AllowedHostsMiddleware`.
  See [middleware](7-middleware.md).
- `cors_config`: An instance of `starlite.config.CORSConfig`. If set this enables the `CORSMiddleware`.
  See [middleware](7-middleware.md).
- `debug`: A boolean flag toggling debug mode on and off, if True, 404 errors will be rendered as HTML with a stack
  trace. This option should _not_ be used in production. Default to `False`.
- `dependencies`: A dictionary mapping dependency providers. See [dependency-injection](6-dependency-injection.md).
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions.
  See [exception-handlers](#exception-handling).
- `guards`: A list of callables. See [guards](9-guards.md).
- `middleware`: A list of classes adhering to the Starlite `MiddlewareProtocol`, instance of the Starlette `Middleware`
  class, or subclasses of the Starlette `BaseHTTPMiddleware` class. See [middleware](7-middleware.md).
- `on_shutdown`: A list of callables that are called during the application shutdown. See [startup-and-shutdown](#startup-and-shutdown).
- `on_startup`: A list of callables that are called during the application startup. See [startup-and-shutdown](#startup-and-shutdown).
- `openapi_config`: An instance of `starlite.config.OpenAPIConfig`. Defaults to the baseline config.
  See [open-api](12-openapi.md).
- `response_class`: A custom response class to be used as the app default.
  See [using-custom-responses](5-responses.md#using-custom-responses).
- `response_headers`: A dictionary of `ResponseHeader` instances.
  See [response-headers](5-responses.md#response-headers).
- `before_request`: a sync or async function to execute before a `Request` is passed to any route handler. If this
  function returns a value, the request will not reach the route handler, and instead this value will be used.
- `after_request`: a sync or async function to execute before the `Response` is returned. This function receives the
  `Respose` object and it must return a `Response` object.
- `static_files_config`: an instance or list of `starlite.config.StaticFilesConfig`. See [static files](#static-files).

## Startup and Shutdown

You can pass a list of callables, **sync and/or async**, using the `on_startup` / `on_shutdown` kwargs. These callables will
be called when the ASGI server (uvicorn, dafne etc.) emits the respective "startup" or "shutdown" event.

A classic use case for this is **database connectivity**. Often you will want to **establish** the connection **once** – on
application startup, and then **close** the connection on shutdown.

For example, lets assume we **create a connection** to a Postgres DB using the async engine from [SQLAlchemy](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html), and
we therefore opt to create **two functions**, one to get or **establish the connection**, and another to **close** it:

```python title="my_app/postgres.py"
from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

state: dict[str, AsyncEngine] = {}


def get_postgres_connection() -> AsyncEngine:
    """Returns the Postgres connection. If it doesn't exist, creates it and saves it in a State object"""
    if not state.get("postgres_connection"):
        state["postgres_connection"] = create_async_engine(settings.DATABASE_URI)
    return cast(AsyncEngine, state.get("postgres_connection"))


async def close_postgres_connection() -> None:
    """Closes the postgres connection stored in the given State object"""
    engine = state.get("postgres_connection")
    if engine:
        await cast(AsyncEngine, engine).dispose()
```

We now simply need to **pass these** to the Starlite **init method** to ensure these are called correctly:

```python title="my_app/main.py"
from starlite import Starlite

from my_app.postgres import get_postgres_connection, close_postgres_connection

app = Starlite(on_startup=[get_postgres_connection], on_shutdown=[close_postgres_connection])
```

### Using Application State

**Callables** passed to the `on_startup` / `on_shutdown` hooks can receive either no arguments, or a **single argument** for the
**application state**. The application state is available on the app instance as the `app.state` attribute and it is an
instance of the class `starlite.datastructures.State`, which inherits from `starlette.datastructures.State`.

Let's rewrite the previous examples to use the application state:

```python title="my_app/postgres.py"
from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from starlite.datastructures import State

from app.config import settings

def get_postgres_connection(state: State) -> AsyncEngine:
    """Returns the Postgres connection. If it doesn't exist, creates it and saves it in a State object"""
    if not hasattr(state, "postgres_connection"):
        state.postgres_connection = create_async_engine(settings.DATABASE_URI)
    return cast(AsyncEngine, state.postgres_connection)


async def close_postgres_connection(state: State) -> None:
    """Closes the postgres connection stored in the given State object"""
    if hasattr(state, "postgres_connection"):
        await cast(AsyncEngine, state.postgres_connection).dispose()
```

The **advantage** of following this pattern is that the application `state` can be **injected** into dependencies and route
handlers. Regarding this see [handler function kwargs](2-route-handlers/1_http_route_handlers.md#handler-function-kwargs).

## Logging

Another **common requirement** for an application startup is **logging**. Although Starlite **does not configure
logging out-of-the box**, it does come with a convenience `pydantic` model called `LoggingConfig`, which you can use like so:

```python title="my_app/main.py"
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

`LoggingConfig` is a convenience wrapper around the standard library's _DictConfig_ options, which can be rather
confusing. It pre-configures logging to use the `QueueHandler`, which is non-blocking and recommended for async applications.

In the above we defined a logger for the "my_app" namespace with a level of "INFO", i.e. only messages of INFO severity
or above will be logged by it, using the `LoggingConfig` default console handler, which will emit logging messages to \*
sys.stderr\_ using the `QueueHandler`.

You do not need to use `LoggingConfig` to set up logging. This is completely decoupled from Starlite itself, and you are
**free to use whatever solution** you want for this (e.g. [loguru](https://github.com/Delgan/loguru)). Still, if you do set
up logging - then the on_startup hook is a good place to do this.

## Exceptions

The Starlite `HTTPException` class can receive 3 optional kwargs:

- `detail`: The error message. Defaults to the "phrase" of the status code using `http.HttpStatus`.
- `status_code`: A valid HTTP error status code (4xx or 5xx range). Defaults to 500.
- `extra`: A dictionary of arbitrary values. This dictionary will be serialized and sent as part of the response.
  Defaults to `None`.

Starlite also offers several pre-configured **exception subclasses** with pre-set error codes that you can use:

- `ImproperlyConfiguredException`: status code 500. Used internally for configuration errors.
- `ValidationException`: status code 400. This is the exception raised when validation or parsing fails.
- `NotFoundException`: status code 404.
- `NotAuthorizedException`: status code 401.
- `PermissionDeniedException`: status code 403.
- `InternalServerException`: status code 500.
- `ServiceUnavailableException`: status code 503.

## Exception Handling

Starlite handles all errors by default by transforming them into **JSON responses**. If the errors are **instances of** either
the `starlette.exceptions.HTTPException` or the `starlite.exceptions.HTTPException`, the responses will include the
appropriate `status_code`. Otherwise, the responses will **default to 500** - "Internal Server Error".

You can **customize exception handling** by passing a dictionary – mapping either `error status codes`, or `exception classes`, to
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

The above will define a top level exception handler that will apply the `plain_text_exception_handler` function to all
exceptions that inherit from `HTTPException`. You could of course be more granular:

```python
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlite import ValidationException, Request, Response, Starlite


def first_exception_handler(request: Request, exc: Exception) -> Response:
    ...


def second_exception_handler(request: Request, exc: Exception) -> Response:
    ...


def third_exception_handler(request: Request, exc: Exception) -> Response:
    ...


app = Starlite(
    route_handlers=[...],
    exception_handlers={
        ValidationException: first_exception_handler,
        HTTP_500_INTERNAL_SERVER_ERROR: second_exception_handler,
        ValueError: third_exception_handler,
    },
)
```

The choice whether to use a single function that has switching logic inside it, or multiple functions depends on your
specific needs.

While it does not make much sense to have different functions with a top-level exception handling,
Starlite supports defining exception handlers on all levels of the app, with the lower levels overriding levels above
them. Thus, in the following example, the exception handler for the route handler function will handle the `ValidationException` related to it:

```python
from starlite import (
    HTTPException,
    ValidationException,
    Request,
    Response,
    Starlite,
    get,
)


def top_level_handler(request: Request, exc: Exception) -> Response:
    ...


def handler_level_handler(request: Request, exc: Exception) -> Response:
    ...


@get("/greet", exception_handlers={ValidationException: top_level_handler})
def my_route_handler(name: str) -> str:
    return f"hello {name}"


app = Starlite(
    route_handlers=[my_route_handler],
    exception_handlers={HTTPException: top_level_handler},
)
```

## Static Files

Static files are files served by the app from predefined locations. To configure static file serving, either **pass an
instance of `starlite.config.StaticFilesConfig` or a list thereof** to the Starlite constructor using
the `static_files_config` kwarg.

For example, lets say our Starlite app is going to serve **regular files** from the "my_app/static" folder and **html documents** from
the "my_app/html" folder, and we would like to serve the **static files** on the "/files" path, and the **html files** on the "/html"
path:

```python
from starlite import Starlite, StaticFilesConfig

app = Starlite(
    route_handlers=[...],
    static_files_config=[
        StaticFilesConfig(directories=["static"], path="/files"),
        StaticFilesConfig(directories=["html"], path="/html", html_mode=True),
    ],
)
```

Matching is done based on filename: Assumed we have a request that is trying to retrieve the path
`/files/file.txt`, the **directory for the base path** `/files` **will be searched** for the file `file.txt`. If it is
found, the file will be sent over, otherwise a **404 response** will be sent.

If `html_mode` is enabled and no specific file is requested, the application will fallback to serving `index.html`. If
no file is found the application will look for a `404.html` file in order to render a response, otherwise a 404 `NotFoundException`
will be returned.
