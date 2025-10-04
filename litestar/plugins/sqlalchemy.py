# ruff: noqa: F401, PLC0415, TC004, RUF100
# pyright: reportUnusedImport=false
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

warn_deprecation(
    deprecated_name="litestar.plugins.sqlalchemy",
    version="2.18.0",
    kind="import",
    removal_in="3.0.0",
    info="The 'litestar.plugins.sqlalchemy' module is deprecated. "
    "Please import directly from 'advanced_alchemy.extensions.litestar' instead.",
)

__all__ = (
    "AlembicAsyncConfig",
    "AlembicCommands",
    "AlembicSyncConfig",
    "AsyncSessionConfig",
    # deprecated
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
    "exceptions",
    "filters",
    "mixins",
    "operations",
    "orm_registry",
    "repository",
    "service",
    "sync_autocommit_before_send_handler",
    "sync_autocommit_handler_maker",
    "sync_default_before_send_handler",
    "sync_default_handler_maker",
    "types",
    "utils",
)


def __getattr__(attr_name: str) -> object:
    _deprecated_attrs = {
        "AuditColumns",
        "BigIntAuditBase",
        "BigIntBase",
        "BigIntPrimaryKey",
        "CommonTableAttributes",
        "UUIDAuditBase",
        "UUIDBase",
        "UUIDPrimaryKey",
        "orm_registry",
    }

    if attr_name in _deprecated_attrs:
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

        warn_deprecation(
            deprecated_name=f"litestar.plugins.sqlalchemy.{attr_name}",
            version="2.9.0",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.plugins.sqlalchemy' is deprecated, please"
            f"import it from 'litestar.plugins.sqlalchemy.base.{attr_name}' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value
    if attr_name in set(__all__).difference(_deprecated_attrs):
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

        value = globals()[attr_name] = locals()[attr_name]
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
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
