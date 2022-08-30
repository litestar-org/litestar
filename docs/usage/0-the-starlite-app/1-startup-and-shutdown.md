# Startup and Shutdown

You can pass a list of callables - either sync or async functions, methods or class instances - using the `on_startup`
/ `on_shutdown` kwargs of the `Starlite` constructor. The callables will be called in their respective order in the list
once the ASGI server (uvicorn, dafne etc.) emits the respective event.

## Example

A classic use case for this is database connectivity. Often, we want to establish a database connection on application
startup, and then close it gracefully upon shutdown.

For example, lets create a database connection using the async engine from
[SQLAlchemy](https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html). We create two functions, one to get or
establish the connection, and another to close it, and then pass them to the Starlite constructor:

```py title="Startup and Shutdown"
--8<-- "examples/startup_and_shutdown.py"
```
