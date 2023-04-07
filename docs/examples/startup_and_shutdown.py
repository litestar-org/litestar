from typing import TYPE_CHECKING, cast

from pydantic import BaseSettings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from litestar import Litestar

if TYPE_CHECKING:
    from litestar.datastructures import State


class AppSettings(BaseSettings):
    DATABASE_URI: str = "postgresql+asyncpg://postgres:mysecretpassword@pg.db:5432/db"


settings = AppSettings()


def get_db_connection(state: "State") -> AsyncEngine:
    """Returns the db engine.

    If it doesn't exist, creates it and saves it in on the application state object
    """
    if not getattr(state, "engine", None):
        state.engine = create_async_engine(settings.DATABASE_URI)
    return cast("AsyncEngine", state.engine)


async def close_db_connection(state: "State") -> None:
    """Closes the db connection stored in the application State object."""
    if getattr(state, "engine", None):
        await cast("AsyncEngine", state.engine).dispose()


app = Litestar(on_startup=[get_db_connection], on_shutdown=[close_db_connection])
