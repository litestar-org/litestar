# This file has been replaced by a package structure.
# The content has been moved to litestar/plugins/sqlalchemy/__init__.py
# This file is kept for backward compatibility and will be removed in a future version.

# Re-export all symbols from the package to maintain backward compatibility
from advanced_alchemy import (
    base,
    exceptions,
    filters,
    mixins,
    operations,
    repository,
    service,
    types,
    utils,
)
from advanced_alchemy.base import (
    AuditColumns,
    BigIntAuditBase,
    BigIntBase,
    BigIntPrimaryKey,
    CommonTableAttributes,
    UUIDAuditBase,
    UUIDBase,
    UUIDPrimaryKey,
    orm_registry,
)
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
    sync_autocommit_before_send_handler,
    sync_autocommit_handler_maker,
    sync_default_before_send_handler,
    sync_default_handler_maker,
)

# Also import from the new package structure to ensure any package-specific functionality is available
from litestar.plugins.sqlalchemy import repository as _repository  # noqa
