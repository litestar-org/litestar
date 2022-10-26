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


sqlalchemy_plugin = SQLAlchemyPlugin(
    config=SQLAlchemyConfig(
        connection_string="sqlite+aiosqlite://",
    )
)
session_config = SQLAlchemyBackendConfig(
    plugin=sqlalchemy_plugin,
    model=SessionModel,
)

app = Starlite(
    route_handlers=[],
    middleware=[session_config.middleware],
    plugins=[sqlalchemy_plugin],
)
