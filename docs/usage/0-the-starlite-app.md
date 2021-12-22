# The Starlite App

At the root of every Starlite application is an instance of the `Starlite` class or a subclass of it. Typically, this
code will be placed in a file called `main.py` at the project's source folder root.

Instantiating the app is straightforward:

```python
# my_api/main.py

from starlite import Starlite

app = Starlite()
```

The `Starlite` class supports the following kwargs, all of which are optional:

* `debug`: a boolean flag toggling debug mode on and off, if True 404 errors will be rendered as HTML with a stack
  trace. This option should *not* be used in production. Default: `False`.
* `on_startup`: a list of sync and/or async callables that are called during the application startup
* `on_shutdown`: a list of sync and/or async callables that are called during the application shutdown
* `middleware`: a list of starlette `Middleware` instances or classes extending `BaseHTTPMiddleware`.
  See [middleware](4-middleware.md) for further details.
* `exception_handlers`: a dictionary mapping exceptions or exception codes to callables.
  See [exception-handlers](5-exceptions.md) for further details.
* `route_handlers`: a list of route handlers, see [route-handlers](1-route-handlers.md) for further details.
* `dependencies`: a dictionary mapping string keys to dependencies.
  See [dependency-injection](3-dependency-injection.md) for further details.

## Lifecycle

Starlette, on top of which StatLite is built, supports two kinds of application lifecycle management - `on_statup`
/ `on_shutdown` hooks, which accept a sequence of callables, and `lifespan`, which accepts an `AsyncContextManager`. To
simplify matters, Starlite only supports the `on_statup` / `on_shutdown` hooks. To use these you can pass a __list__ of
callables - sync and/or async - which will be called respectively during the application startup and shutdown.

A classic example of this would be establishing a connection to a DB on startup and closing it on shutdown. For example,
lets assume we create establish a connection to a Postgres DB using the async engine
from [SQLAlchemy](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html). We might thus create two functions,
one to get or create the connection, and another to close it:

```python
# my_api/postgres.py

from os import environ
from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from starlette.datastructures import State

state = State()


def get_postgres_connection() -> AsyncEngine:
    """Returns the Postgres connection. If it doesn't exist, creates it and saves it in a State object"""
    postgres_connection_string = environ.get("POSTGRES_CONNECTION_STRING", "")
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

We now simply need to pass these to the Starlite init method to ensure these are called correctly:

```python
# my_api/main.py

from starlite import Starlite

from my_api.postgres import get_postgres_connection, close_postgres_connection

app = Starlite(on_startup=[get_postgres_connection], on_shutdown=[close_postgres_connection])
```

## Logging

Another thing most applications will need to set up as part of the application startup is logging. Although Starlite
does not configure logging for you, it does come with a convenience `pydantic` model called `LoggingConfig`, which you
can use like so:

```python
# my_api/main.py

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

`LoggingConfig` is merely a convenience wrapper around the standard library's DictConfig options, which can be rather
confusing. In the above we defined a logger for the "my_app" namespace with a level of "INFO", i.e. only messages of
INFO severity or above will be logged by it. We also defined it, so it will log using the `LoggingConfig` default console
handler, which will emit logging messages to _sys.stderr_.

You do not need to use `LoggingConfig` to set up logging. This is completely decoupled from Starlite itself, and you are
free to use whatever solution you want for this (e.g. [loguru](https://github.com/Delgan/loguru)). Still, if you do
setup up logging - then the on_startup hook is a good place to do so.
