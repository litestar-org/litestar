def test_re_exports() -> None:
    from advanced_alchemy.extensions import litestar as sa_litestar
    from advanced_alchemy.extensions.litestar import exceptions as sa_exceptions
    from advanced_alchemy.extensions.litestar import filters as sa_filters
    from advanced_alchemy.extensions.litestar import repository as sa_repository
    from advanced_alchemy.extensions.litestar import service as sa_service
    from advanced_alchemy.extensions.litestar import types as sa_types
    from advanced_alchemy.extensions.litestar import utils as sa_utils

    from litestar.plugins import sqlalchemy

    assert sqlalchemy.filters is sa_filters
    assert sqlalchemy.types is sa_types
    assert sqlalchemy.utils is sa_utils
    assert sqlalchemy.repository is sa_repository
    assert sqlalchemy.service is sa_service
    assert sqlalchemy.exceptions is sa_exceptions

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
