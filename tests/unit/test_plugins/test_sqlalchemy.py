from advanced_alchemy.extensions import litestar as sa_litestar
from advanced_alchemy.extensions.litestar import base as sa_base
from advanced_alchemy.extensions.litestar import filters as sa_filters
from advanced_alchemy.extensions.litestar import mixins as sa_mixins
from advanced_alchemy.extensions.litestar import service as sa_service
from advanced_alchemy.extensions.litestar import types as sa_types

from litestar.pagination import OffsetPagination
from litestar.plugins import sqlalchemy


def test_re_exports() -> None:
    # Test static submodule re-exports - these are local modules that re-export from advanced_alchemy
    # We check that the key exports are available rather than module identity
    from litestar.plugins.sqlalchemy import base, exceptions, repository  # noqa: PLC0415

    # Verify base module exports
    assert hasattr(base, "BigIntAuditBase")
    assert base.BigIntAuditBase is sa_base.BigIntAuditBase
    assert hasattr(base, "orm_registry")
    assert base.orm_registry is sa_base.orm_registry

    # Verify exceptions module exports
    assert hasattr(exceptions, "wrap_sqlalchemy_exception")

    # Verify repository module exports
    assert hasattr(repository, "SQLAlchemyAsyncRepository")
    assert hasattr(repository, "SQLAlchemySyncRepository")
    assert hasattr(repository, "ModelT")

    # Test dynamic submodules - these are proxies so we check key attributes instead of identity
    assert hasattr(sqlalchemy.filters, "FilterTypes")
    assert sqlalchemy.filters.FilterTypes is sa_filters.FilterTypes
    assert hasattr(sqlalchemy.types, "GUID")
    assert sqlalchemy.types.GUID is sa_types.GUID
    assert hasattr(sqlalchemy.mixins, "AuditColumns")
    assert sqlalchemy.mixins.AuditColumns is sa_mixins.AuditColumns
    assert hasattr(sqlalchemy.service, "OffsetPagination")
    assert sqlalchemy.service.OffsetPagination is sa_service.OffsetPagination
    assert OffsetPagination is sa_service.OffsetPagination

    assert sqlalchemy.AlembicAsyncConfig is sa_litestar.AlembicAsyncConfig
    assert sqlalchemy.AlembicCommands is sa_litestar.AlembicCommands
    assert sqlalchemy.AlembicSyncConfig is sa_litestar.AlembicSyncConfig
    assert sqlalchemy.AsyncSessionConfig is sa_litestar.AsyncSessionConfig
    assert sqlalchemy.EngineConfig is sa_litestar.EngineConfig
    assert sqlalchemy.SQLAlchemyAsyncConfig is sa_litestar.SQLAlchemyAsyncConfig
    assert sqlalchemy.SQLAlchemyDTO is sa_litestar.SQLAlchemyDTO
    assert sqlalchemy.SQLAlchemyDTOConfig is sa_litestar.SQLAlchemyDTOConfig
    assert sqlalchemy.SQLAlchemyInitPlugin is sa_litestar.SQLAlchemyInitPlugin
    assert sqlalchemy.SQLAlchemyPlugin is sa_litestar.SQLAlchemyPlugin
    assert sqlalchemy.SQLAlchemySerializationPlugin is sa_litestar.SQLAlchemySerializationPlugin
    assert sqlalchemy.SQLAlchemySyncConfig is sa_litestar.SQLAlchemySyncConfig
    assert sqlalchemy.SyncSessionConfig is sa_litestar.SyncSessionConfig

    # v3.0: No more deprecation warnings, these are now direct exports
    assert sqlalchemy.AuditColumns is sa_mixins.AuditColumns
    assert sqlalchemy.BigIntAuditBase is sa_base.BigIntAuditBase
    assert sqlalchemy.BigIntBase is sa_base.BigIntBase
    assert sqlalchemy.BigIntPrimaryKey is sa_mixins.BigIntPrimaryKey
    assert sqlalchemy.CommonTableAttributes is sa_base.CommonTableAttributes
    assert sqlalchemy.UUIDAuditBase is sa_base.UUIDAuditBase
    assert sqlalchemy.UUIDBase is sa_base.UUIDBase
    assert sqlalchemy.UUIDPrimaryKey is sa_mixins.UUIDPrimaryKey
    assert sqlalchemy.orm_registry is sa_base.orm_registry
