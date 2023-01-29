from sqlalchemy.orm import declarative_base

from starlite import Starlite
from starlite.middleware.session.sqlalchemy_backend import (
    SQLAlchemyBackendConfig,
    create_session_model,
)
from starlite.plugins.sqlalchemy import SQLAlchemyConfig, SQLAlchemyPlugin

Base = declarative_base()

sqlalchemy_config = SQLAlchemyConfig(connection_string="sqlite+pysqlite://", use_async_engine=False)
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)

SessionModel = create_session_model(Base)

session_config = SQLAlchemyBackendConfig(plugin=sqlalchemy_plugin, model=SessionModel)


def on_startup() -> None:
    """Initialize the database."""
    Base.metadata.create_all(sqlalchemy_config.engine)  # type: ignore


app = Starlite(
    route_handlers=[],
    middleware=[session_config.middleware],
    plugins=[sqlalchemy_plugin],
    on_startup=[on_startup],
)
