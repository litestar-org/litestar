===========
ASGI Events
===========

You can pass a list of `callables` - either synchrnous/asynchronous functions, methods or
class instances to the ``on_startup`` or ``on_shutdown`` keyword parameters of the
`Starlite instance <./reference/1-app/#starlite.app.Starlite>`_. Those will be called in
order, once the ASGI server (like ``uvicorn``, ``daphne``, etc) emits the respective
event.

.. TODO: Reconsidering using a "mermaid" extension for Sphinx so as to not compromise on
   the quality of image assets.

.. image:: ../images/starlite-events.svg
   :alt: Flow chart diagram of the ASGI events of a Starlite application.

A classic use case for this is database connectivity. Often we want to establish a
database connection on application startup & then close the connection gracefully upon
application shutdown.

For example, lets create a database connection using the async engine from
`SQLAlchemy <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html>`_. We create
two functions, one to get or establish the database connection & the other to close it.
These functions can then be passed to the Starlite constructor.

.. code-block:: python

    from typing import cast

    from pydantic import BaseSettings
    from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

    from starlite import Starlite, State


    class AppSettings(BaseSettings):
        DATABASE_URI: str = "postgresql+asyncpg://postgres:mysecretpassword@pg.db:5432/db"


    settings = AppSettings()


    def get_db_connection(state: State) -> AsyncEngine:
        """Returns the db engine.

        If it doesn't exist, creates it and saves it in on the application state object
        """
        if not getattr(state, "engine", None):
            state.engine = create_async_engine(settings.DATABASE_URI)
        return cast("AsyncEngine", state.engine)


    async def close_db_connection(state: State) -> None:
        """Closes the db connection stored in the application State object."""
        if getattr(state, "engine", None):
            await cast("AsyncEngine", state.engine).dispose()


    app = Starlite(
        route_handlers=[], on_startup=[get_db_connection], on_shutdown=[close_db_connection]
    )
