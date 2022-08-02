# Startup and Shutdown

You can pass a list of callables - either sync or async functions, methods or class instances - using the `on_startup`
/ `on_shutdown` kwargs of the `Starlite` constructor. The callables will be called in their respective order in the list
once the ASGI server (uvicorn, dafne etc.) emits the respective event.

## Example

A classic use case for this is database connectivity. Often, we want to establish a database connection once on
application startup, and then close it gracefully upon shutdown.

For example, lets assume we create a connection to a Postgres DB using the async engine from
[SQLAlchemy](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html). We will therefore opt to create two
functions, one to get or establish the connection, and another to close it, and then pass them to the Starlite
constructor:

```python
from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from starlite import Starlite, State
from pydantic import BaseSettings


class AppSettings(BaseSettings):
    POSTGRES_CONNECTION_STRING: str


settings = AppSettings()


def get_postgres_connection(state: State) -> AsyncEngine:
    """Returns the Postgres connection. If it doesn't exist, creates it and saves it in on the application state object"""
    if not state.postgres_connection:
        state.postgres_connection = create_async_engine(
            settings.POSTGRES_CONNECTION_STRING
        )
    return cast("AsyncEngine", state.postgres_connection)


async def close_postgres_connection(state: State) -> None:
    """Closes the postgres connection stored in the application State object"""
    if state.postgres_connection:
        await cast("AsyncEngine", state.postgres_connection).engine.dispose()
    return None


app = Starlite(
    on_startup=[get_postgres_connection], on_shutdown=[close_postgres_connection]
)
```
