from starlite.utils.deprecation import warn_deprecation

from .config import SQLAlchemyConfig, SQLAlchemyEngineConfig, SQLAlchemySessionConfig
from .plugin import SQLAlchemyPlugin

__all__ = ("SQLAlchemyPlugin", "SQLAlchemyConfig", "SQLAlchemyEngineConfig", "SQLAlchemySessionConfig", "config")

warn_deprecation(
    version="v1.51.0",
    deprecated_name="starlite.plugins.sql_alchemy",
    removal_in="v2.0.0",
    alternative="starlite.plugins.sqlalchemy",
    kind="import",
)
