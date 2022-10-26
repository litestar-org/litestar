from sqlalchemy.orm import declarative_base

from starlite import Starlite
from starlite.middleware.session.sqlalchemy_backend import (
    SQLAlchemyBackendConfig,
    create_session_model,
)
from starlite.plugins.sql_alchemy import SQLAlchemyConfig, SQLAlchemyPlugin

Base = declarative_base()

SessionModel = create_session_model(Base)

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
