from __future__ import annotations

from .init import (
    AsyncSessionConfig,
    EngineConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
    SQLAlchemySyncConfig,
    SyncSessionConfig,
)
from .serialization import SQLAlchemySerializationPlugin


class SQLAlchemyPlugin(SQLAlchemyInitPlugin, SQLAlchemySerializationPlugin):
    """A plugin that provides SQLAlchemy integration."""


__all__ = (
    "AsyncSessionConfig",
    "EngineConfig",
    "SQLAlchemyAsyncConfig",
    "SQLAlchemyInitPlugin",
    "SQLAlchemyPlugin",
    "SQLAlchemySerializationPlugin",
    "SQLAlchemySyncConfig",
    "SyncSessionConfig",
)
