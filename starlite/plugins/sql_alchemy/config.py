from starlite.utils.deprecation import warn_deprecation

from ..sqlalchemy.config import (
    SESSION_SCOPE_KEY,
    SESSION_TERMINUS_ASGI_EVENTS,
    IsolationLevel,
    SQLAlchemyConfig,
    SQLAlchemyEngineConfig,
    SQLAlchemySessionConfig,
    default_before_send_handler,
    serializer,
)

__all__ = (
    "IsolationLevel",
    "SESSION_SCOPE_KEY",
    "SESSION_TERMINUS_ASGI_EVENTS",
    "SQLAlchemyConfig",
    "SQLAlchemyEngineConfig",
    "SQLAlchemySessionConfig",
    "default_before_send_handler",
    "serializer",
)

warn_deprecation(
    version="v1.51.0",
    deprecated_name="starlite.plugins.sql_alchemy.config",
    removal_in="v2.0.0",
    alternative="starlite.plugins.sqlalchemy.config",
    kind="import",
)
