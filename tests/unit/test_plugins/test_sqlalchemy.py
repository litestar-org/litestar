from advanced_alchemy import base as sa_base
from advanced_alchemy import filters as sa_filters
from advanced_alchemy import types as sa_types
from advanced_alchemy.extensions import litestar as sa_litestar

from litestar.plugins import sqlalchemy
from __future__ import annotations

import pytest
from advanced_alchemy import repository as advanced_alchemy_repo
from advanced_alchemy import types as advanced_alchemy_types
from advanced_alchemy.repository import typing as advanced_alchemy_typing
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from litestar.plugins.sqlalchemy import SQLAlchemyAsyncConfig, SQLAlchemySyncConfig

 
def test_create_engine_with_engine_instance() -> None:
    engine = create_engine("sqlite:///:memory:")
    config = SQLAlchemySyncConfig(engine_instance=engine)
    with pytest.deprecated_call():
        assert engine is config.get_engine()


def test_create_engine_with_connection_string() -> None:
    config = SQLAlchemySyncConfig(connection_string="sqlite:///:memory:")
    with pytest.deprecated_call():
        engine = config.get_engine()
    assert isinstance(engine, Engine)


def test_async_create_engine_with_engine_instance() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    config = SQLAlchemyAsyncConfig(engine_instance=engine)
    with pytest.deprecated_call():
        assert engine is config.get_engine()


def test_async_create_engine_with_connection_string() -> None:
    config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///:memory:")
    with pytest.deprecated_call():
        engine = config.get_engine()
    assert isinstance(engine, AsyncEngine)


def test_repository_re_exports() -> None:
    from advanced_alchemy.repository import types as repository_types

    from litestar.plugins.sqlalchemy import (
        SQLAlchemyAsyncRepository,
        SQLAlchemySyncRepository,
        types,
        wrap_sqlalchemy_exception,
    )

    assert SQLAlchemySyncRepository is advanced_alchemy_repo.SQLAlchemySyncRepository
    assert SQLAlchemyAsyncRepository is advanced_alchemy_repo.SQLAlchemyAsyncRepository
    assert wrap_sqlalchemy_exception is advanced_alchemy_repo._util.wrap_sqlalchemy_exception

    assert repository_types.ModelT is advanced_alchemy_typing.ModelT
    assert repository_types.RowT is advanced_alchemy_typing.RowT
    assert repository_types.SQLAlchemyAsyncRepositoryT is advanced_alchemy_typing.SQLAlchemyAsyncRepositoryT
    assert repository_types.SQLAlchemySyncRepositoryT is advanced_alchemy_typing.SQLAlchemySyncRepositoryT

    assert types.GUID is advanced_alchemy_types.GUID
    assert types.ORA_JSONB is advanced_alchemy_types.ORA_JSONB
    assert types.BigIntIdentity is advanced_alchemy_types.BigIntIdentity
    assert types.DateTimeUTC is advanced_alchemy_types.DateTimeUTC
    assert types.JsonB is advanced_alchemy_types.JsonB


def test_re_exports() -> None:
    assert sqlalchemy.filters is sa_filters
    assert sqlalchemy.types is sa_types

    assert sqlalchemy.AuditColumns is sa_base.AuditColumns
    assert sqlalchemy.BigIntAuditBase is sa_base.BigIntAuditBase
    assert sqlalchemy.BigIntBase is sa_base.BigIntBase
    assert sqlalchemy.BigIntPrimaryKey is sa_base.BigIntPrimaryKey
    assert sqlalchemy.CommonTableAttributes is sa_base.CommonTableAttributes
    assert sqlalchemy.UUIDAuditBase is sa_base.UUIDAuditBase
    assert sqlalchemy.UUIDBase is sa_base.UUIDBase
    assert sqlalchemy.UUIDPrimaryKey is sa_base.UUIDPrimaryKey
    assert sqlalchemy.orm_registry is sa_base.orm_registry

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
