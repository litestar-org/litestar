from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from starlite import Starlite
from starlite.middleware.session.sqlalchemy_backend import (
    SessionModelMixin,
    SQLAlchemyBackendConfig,
)
from starlite.plugins.sql_alchemy import SQLAlchemyConfig, SQLAlchemyPlugin

Base = declarative_base()


class SessionModel(Base, SessionModelMixin):  # pyright: ignore [reportGeneralTypeIssues]
    __tablename__ = "my-session-table"
    id = Column(Integer, primary_key=True)
    additional_data = Column(String)


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


app = Starlite(middleware=[session_config.middleware], plugins=[sqlalchemy_plugin], on_startup=[on_startup])
