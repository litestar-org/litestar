from typing import cast

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from litestar import Litestar


class AppSettings(BaseSettings):
    DATABASE_URI: str = "postgresql+asyncpg://postgres:mysecretpassword@pg.db:5432/db"


settings = AppSettings()


def get_db_connection(app: Litestar) -> AsyncEngine:
    """Returns the db engine.

    If it doesn't exist, creates it and saves it in on the application state object
    """
    if not getattr(app.state, "engine", None):
        app.state.engine = create_async_engine(settings.DATABASE_URI)
    return cast("AsyncEngine", app.state.engine)


async def close_db_connection(app: Litestar) -> None:
    """Closes the db connection stored in the application State object."""
    if getattr(app.state, "engine", None):
        await cast("AsyncEngine", app.state.engine).dispose()


app = Litestar(on_startup=[get_db_connection], on_shutdown=[close_db_connection])
