# pyright: reportUnusedImport=false
"""SQLAlchemy plugin for Litestar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.exceptions import MissingDependencyException

__all__ = (
    "AlembicAsyncConfig",
    "AlembicCommands",
    "AlembicSyncConfig",
    "AsyncSessionConfig",
    "AuditColumns",
    "BigIntAuditBase",
    "BigIntBase",
    "BigIntPrimaryKey",
    "CommonTableAttributes",
    "EngineConfig",
    "SQLAlchemyAsyncConfig",
    "SQLAlchemyDTO",
    "SQLAlchemyDTOConfig",
    "SQLAlchemyInitPlugin",
    "SQLAlchemyPlugin",
    "SQLAlchemySerializationPlugin",
    "SQLAlchemySyncConfig",
    "SyncSessionConfig",
    "UUIDAuditBase",
    "UUIDBase",
    "UUIDPrimaryKey",
    "async_autocommit_before_send_handler",
    "async_autocommit_handler_maker",
    "async_default_before_send_handler",
    "async_default_handler_maker",
    "base",
    "dto",
    "exceptions",
    "filters",
    "get_database_migration_plugin",
    "mixins",
    "operations",
    "orm_registry",
    "repository",
    "service",
    "sync_autocommit_before_send_handler",
    "sync_autocommit_handler_maker",
    "sync_default_before_send_handler",
    "sync_default_handler_maker",
    "touch_updated_timestamp",
    "types",
    "utils",
)

# Try to import advanced_alchemy, providing helpful error if not available
try:
    # Import all the submodules
    # Import main exports from advanced_alchemy.extensions.litestar
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
        get_database_migration_plugin,
        sync_autocommit_before_send_handler,
        sync_autocommit_handler_maker,
        sync_default_before_send_handler,
        sync_default_handler_maker,
    )

    from . import base, dto, exceptions, filters, mixins, operations, repository, service, types, utils

    # Import and re-export from base
    from .base import (
        AuditColumns,
        BigIntAuditBase,
        BigIntBase,
        BigIntPrimaryKey,
        CommonTableAttributes,
        UUIDAuditBase,
        UUIDBase,
        UUIDPrimaryKey,
        orm_registry,
        touch_updated_timestamp,
    )
except ImportError as e:
    raise MissingDependencyException("advanced-alchemy", extra="sqlalchemy") from e


if TYPE_CHECKING:
    # Re-export submodules for type checking
    from . import base as base  # noqa: PLC0414, TC004
    from . import dto as dto  # noqa: PLC0414, TC004
    from . import exceptions as exceptions  # noqa: PLC0414, TC004
    from . import filters as filters  # noqa: PLC0414, TC004
    from . import mixins as mixins  # noqa: PLC0414, TC004
    from . import operations as operations  # noqa: PLC0414, TC004
    from . import repository as repository  # noqa: PLC0414, TC004
    from . import service as service  # noqa: PLC0414, TC004
    from . import types as types  # noqa: PLC0414, TC004
    from . import utils as utils  # noqa: PLC0414, TC004
