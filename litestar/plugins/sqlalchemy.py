from __future__ import annotations

from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    AlembicCommands,
    AlembicSyncConfig,
    AsyncSessionConfig,
    EngineConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyDTO,
    SQLAlchemyDTOConfig,
    SQLAlchemyInitPlugin,
    SQLAlchemyPlugin,
    SQLAlchemySerializationPlugin,
    SQLAlchemySyncConfig,
    SyncSessionConfig,
    async_autocommit_before_send_handler,
    async_autocommit_handler_maker,
    async_default_before_send_handler,
    async_default_handler_maker,
    base,
    exceptions,
    filters,
    mixins,
    operations,
    repository,
    service,
    sync_autocommit_before_send_handler,
    sync_autocommit_handler_maker,
    sync_default_before_send_handler,
    sync_default_handler_maker,
    types,
    utils,
)

from litestar.utils import warn_deprecation

__all__ = (
    "filters",
    "utils",
    "operations",
    "base",
    "types",
    "repository",
    "service",
    "mixins",
    "exceptions",
    "async_autocommit_handler_maker",
    "sync_autocommit_handler_maker",
    "async_default_handler_maker",
    "sync_default_handler_maker",
    "sync_autocommit_before_send_handler",
    "async_autocommit_before_send_handler",
    "sync_default_before_send_handler",
    "async_default_before_send_handler",
    "AlembicCommands",
    "AlembicAsyncConfig",
    "AlembicSyncConfig",
    "AsyncSessionConfig",
    "SyncSessionConfig",
    "SQLAlchemyDTO",
    "SQLAlchemyDTOConfig",
    "SQLAlchemyAsyncConfig",
    "SQLAlchemyInitPlugin",
    "SQLAlchemyPlugin",
    "SQLAlchemySerializationPlugin",
    "SQLAlchemySyncConfig",
    "EngineConfig",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in {
        "AuditColumns",
        "BigIntAuditBase",
        "BigIntBase",
        "BigIntPrimaryKey",
        "CommonTableAttributes",
        "UUIDAuditBase",
        "UUIDBase",
        "UUIDPrimaryKey",
        "orm_registry",
    }:
        warn_deprecation(
            deprecated_name=f"litestar.plugins.sqlalchemy.{attr_name}",
            version="2.9.0",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.plugins.sqlalchemy' is deprecated, please"
            f"import it from 'litestar.plugins.sqlalchemy.base.{attr_name}' instead",
        )
        value = globals()[attr_name] = getattr(base, attr_name)
        return value
    if attr_name in __all__:
        return getattr(attr_name, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
