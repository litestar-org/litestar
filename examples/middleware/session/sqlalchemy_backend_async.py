from sqlalchemy.orm import declarative_base

from starlite import Starlite
from starlite.middleware.session.sqlalchemy_backend import (
    SQLAlchemyBackendConfig,
    create_session_model,
)
from starlite.plugins.sql_alchemy import SQLAlchemyConfig, SQLAlchemyPlugin

Base = declarative_base()

SessionModel = create_session_model(Base)

sqlalchemy_config = SQLAlchemyConfig(connection_string="sqlite+aiosqlite://")
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)
session_config = SQLAlchemyBackendConfig(
    plugin=sqlalchemy_plugin,
    model=SessionModel,
)


async def on_startup() -> None:
    """Initialize the database."""
    async with sqlalchemy_config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)  # pyright: ignore


app = Starlite(
    route_handlers=[], middleware=[session_config.middleware], plugins=[sqlalchemy_plugin], on_startup=[on_startup]
)
