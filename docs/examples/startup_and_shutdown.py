import os
from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from litestar import Litestar

DB_URI = os.environ.get(
    "DATABASE_URI", "postgresql+asyncpg://postgres:mysecretpassword@pg.db:5432/db"
)


def get_db_connection(app: Litestar) -> AsyncEngine:
    """Returns the db engine.

    If it does not exist, creates it and saves it in on the application state object
    """
    if not getattr(app.state, "engine", None):
        app.state.engine = create_async_engine(DB_URI)
    return cast("AsyncEngine", app.state.engine)


async def close_db_connection(app: Litestar) -> None:
    """Closes the db connection stored in the application State object."""
    if getattr(app.state, "engine", None):
        await cast("AsyncEngine", app.state.engine).dispose()


app = Litestar(on_startup=[get_db_connection], on_shutdown=[close_db_connection])
