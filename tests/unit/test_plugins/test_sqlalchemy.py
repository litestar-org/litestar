from advanced_alchemy.extensions import litestar as sa_litestar
from advanced_alchemy.extensions.litestar import base as sa_base
from advanced_alchemy.extensions.litestar import exceptions as sa_exceptions
from advanced_alchemy.extensions.litestar import filters as sa_filters
from advanced_alchemy.extensions.litestar import mixins as sa_mixins
from advanced_alchemy.extensions.litestar import repository as sa_repository
from advanced_alchemy.extensions.litestar import service as sa_service
from advanced_alchemy.extensions.litestar import types as sa_types
from advanced_alchemy.extensions.litestar import utils as sa_utils

from litestar.pagination import OffsetPagination
from litestar.plugins import sqlalchemy


def test_re_exports() -> None:
    assert sqlalchemy.base is sa_base
    assert sqlalchemy.filters is sa_filters
    assert sqlalchemy.types is sa_types
    assert sqlalchemy.mixins is sa_mixins
    assert sqlalchemy.utils is sa_utils
    assert sqlalchemy.repository is sa_repository
    assert sqlalchemy.service is sa_service
    assert sqlalchemy.exceptions is sa_exceptions
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

    # deprecated, to be removed later
    assert sqlalchemy.AuditColumns is sa_base.AuditColumns
    assert sqlalchemy.BigIntAuditBase is sa_base.BigIntAuditBase
    assert sqlalchemy.BigIntBase is sa_base.BigIntBase
    assert sqlalchemy.BigIntPrimaryKey is sa_base.BigIntPrimaryKey
    assert sqlalchemy.CommonTableAttributes is sa_base.CommonTableAttributes
    assert sqlalchemy.UUIDAuditBase is sa_base.UUIDAuditBase
    assert sqlalchemy.UUIDBase is sa_base.UUIDBase
    assert sqlalchemy.UUIDPrimaryKey is sa_base.UUIDPrimaryKey
    assert sqlalchemy.orm_registry is sa_base.orm_registry
