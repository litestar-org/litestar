from __future__ import annotations

from .init import (
    AsyncSessionConfig,
    EngineConfig,
    GenericSessionConfig,
    GenericSQLAlchemyConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
    SQLAlchemySyncConfig,
    SyncSessionConfig,
)
from .serialization import SQLAlchemySerializationPlugin


class SQLAlchemyPlugin(SQLAlchemyInitPlugin, SQLAlchemySerializationPlugin):
    """A plugin that provides SQLAlchemy integration."""

    def __init__(self, config: SQLAlchemyAsyncConfig | SQLAlchemySyncConfig) -> None:
        SQLAlchemyInitPlugin.__init__(self, config=config)
        SQLAlchemySerializationPlugin.__init__(self)


__all__ = (
    "AsyncSessionConfig",
    "EngineConfig",
    "GenericSQLAlchemyConfig",
    "GenericSessionConfig",
    "SQLAlchemyAsyncConfig",
    "SQLAlchemyInitPlugin",
    "SQLAlchemyPlugin",
    "SQLAlchemySerializationPlugin",
    "SQLAlchemySyncConfig",
    "SyncSessionConfig",
)
