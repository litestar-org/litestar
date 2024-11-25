# ruff: noqa: TCH004, F401
# pyright: reportUnusedImport=false
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from advanced_alchemy import exceptions as advanced_alchemy_exceptions
from advanced_alchemy import repository as advanced_alchemy_repo
from advanced_alchemy import types as advanced_alchemy_types
from advanced_alchemy.repository import typing as advanced_alchemy_typing
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def purge_module(module_names: list[str], path: str | Path) -> None:
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(importlib.util.cache_from_source(path)).unlink(missing_ok=True)  # type: ignore[arg-type]


def test_create_engine_with_engine_instance() -> None:
    from litestar.contrib.sqlalchemy.plugins.init.config.sync import SQLAlchemySyncConfig

    engine = create_engine("sqlite:///:memory:")
    config = SQLAlchemySyncConfig(engine_instance=engine)
    with pytest.deprecated_call():
        assert engine is config.create_engine()  # type: ignore[attr-defined]


def test_create_engine_with_connection_string() -> None:
    from litestar.contrib.sqlalchemy.plugins.init.config.sync import SQLAlchemySyncConfig

    config = SQLAlchemySyncConfig(connection_string="sqlite:///:memory:")
    with pytest.deprecated_call():
        engine = config.create_engine()  # type: ignore[attr-defined]
    assert isinstance(engine, Engine)


def test_async_create_engine_with_engine_instance() -> None:
    from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import SQLAlchemyAsyncConfig

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    config = SQLAlchemyAsyncConfig(engine_instance=engine)
    with pytest.deprecated_call():
        assert engine is config.create_engine()  # type: ignore[attr-defined]


def test_async_create_engine_with_connection_string() -> None:
    from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import SQLAlchemyAsyncConfig

    config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///:memory:")
    with pytest.deprecated_call():
        engine = config.create_engine()  # type: ignore[attr-defined]
    assert isinstance(engine, AsyncEngine)


def test_repository_re_exports() -> None:
    from litestar.contrib.sqlalchemy import types
    from litestar.contrib.sqlalchemy.repository import (
        SQLAlchemyAsyncRepository,
        SQLAlchemySyncRepository,
        wrap_sqlalchemy_exception,
    )
    from litestar.contrib.sqlalchemy.repository import types as repository_types

    assert wrap_sqlalchemy_exception is advanced_alchemy_exceptions.wrap_sqlalchemy_exception
    assert SQLAlchemySyncRepository is advanced_alchemy_repo.SQLAlchemySyncRepository
    assert SQLAlchemyAsyncRepository is advanced_alchemy_repo.SQLAlchemyAsyncRepository
    assert repository_types.ModelT is advanced_alchemy_typing.ModelT  # pyright: ignore[reportGeneralTypeIssues]
    assert repository_types.RowT is advanced_alchemy_typing.RowT  # pyright: ignore[reportGeneralTypeIssues]
    assert repository_types.SQLAlchemyAsyncRepositoryT is advanced_alchemy_typing.SQLAlchemyAsyncRepositoryT  # pyright: ignore[reportGeneralTypeIssues]
    assert repository_types.SQLAlchemySyncRepositoryT is advanced_alchemy_typing.SQLAlchemySyncRepositoryT  # pyright: ignore[reportGeneralTypeIssues]

    assert types.GUID is advanced_alchemy_types.GUID
    assert types.ORA_JSONB is advanced_alchemy_types.ORA_JSONB
    assert types.BigIntIdentity is advanced_alchemy_types.BigIntIdentity
    assert types.DateTimeUTC is advanced_alchemy_types.DateTimeUTC
    assert types.JsonB is advanced_alchemy_types.JsonB


def test_deprecated_sqlalchemy_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing SQLAlchemyAsyncRepository from 'litestar.contrib.sqlalchemy' is deprecated"
    ):
        from litestar.contrib.sqlalchemy import SQLAlchemyAsyncRepository
    purge_module(["litestar.contrib.sqlalchemy"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing SQLAlchemySyncRepository from 'litestar.contrib.sqlalchemy' is deprecated"
    ):
        from litestar.contrib.sqlalchemy import SQLAlchemySyncRepository
    purge_module(["litestar.contrib.sqlalchemy"], __file__)
    with pytest.warns(DeprecationWarning, match="importing ModelT from 'litestar.contrib.sqlalchemy' is deprecated"):
        from litestar.contrib.sqlalchemy import ModelT
    purge_module(["litestar.contrib.sqlalchemy"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing wrap_sqlalchemy_exception from 'litestar.contrib.sqlalchemy' is deprecated"
    ):
        from litestar.contrib.sqlalchemy import wrap_sqlalchemy_exception


def test_deprecated_sqlalchemy_plugins_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing AsyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins import AsyncSessionConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing EngineConfig from 'litestar.contrib.sqlalchemy.plugins' is deprecated"
    ):
        from litestar.contrib.sqlalchemy.plugins import EngineConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing GenericSQLAlchemyConfig from 'litestar.contrib.sqlalchemy.plugins' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins import GenericSQLAlchemyConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncConfig from 'litestar.contrib.sqlalchemy.plugins' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins import SQLAlchemyAsyncConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyInitPlugin from 'litestar.contrib.sqlalchemy.plugins' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins import SQLAlchemyInitPlugin


def test_deprecated_sqlalchemy_plugins_init_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing AsyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init import AsyncSessionConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing EngineConfig from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated"
    ):
        from litestar.contrib.sqlalchemy.plugins.init import EngineConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing GenericSQLAlchemyConfig from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init import GenericSQLAlchemyConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncConfig from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init import SQLAlchemyAsyncConfig


def test_deprecated_sqlalchemy_plugins_init_config_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing AsyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins.init.config' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config import AsyncSessionConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing EngineConfig from 'litestar.contrib.sqlalchemy.plugins.init.config' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config import EngineConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing GenericSQLAlchemyConfig from 'litestar.contrib.sqlalchemy.plugins.init.config' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config import GenericSQLAlchemyConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config import SQLAlchemyAsyncConfig


def test_deprecated_sqlalchemy_plugins_init_config_common_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.common"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SESSION_SCOPE_KEY from 'litestar.contrib.sqlalchemy.plugins.init.config.common' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.common import SESSION_SCOPE_KEY
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.common"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SESSION_TERMINUS_ASGI_EVENTS from 'litestar.contrib.sqlalchemy.plugins.init.config.common' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.common import SESSION_TERMINUS_ASGI_EVENTS
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.common"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing GenericSQLAlchemyConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.common' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.common import GenericSQLAlchemyConfig


def test_deprecated_sqlalchemy_plugins_init_config_sync_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.sync"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemySyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.sync import SQLAlchemySyncConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.sync"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing AlembicSyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.sync import AlembicSyncConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.sync"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.sync import SyncSessionConfig


def test_deprecated_sqlalchemy_plugins_init_config_asyncio_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.asyncio"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import SQLAlchemyAsyncConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.asyncio"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing AlembicAsyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import AlembicAsyncConfig
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.asyncio"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing AsyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import AsyncSessionConfig


def test_deprecated_sqlalchemy_plugins_init_config_engine_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.engine"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing EngineConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.engine' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.engine import EngineConfig


def test_deprecated_sqlalchemy_dto_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.dto"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyDTOConfig from 'litestar.contrib.sqlalchemy.dto' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTOConfig


def test_deprecated_sqlalchemy_plugins_init_plugin_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.plugin"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyInitPlugin from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.plugin import SQLAlchemyInitPlugin


def test_deprecated_sqlalchemy_plugins_serialization_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.serialization"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemySerializationPlugin from 'litestar.contrib.sqlalchemy.plugins.serialization' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.serialization import SQLAlchemySerializationPlugin


def test_deprecated_sqlalchemy_repository_async_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.repository._async"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncRepository from 'litestar.contrib.sqlalchemy.repository._async' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.repository._async import SQLAlchemyAsyncRepository


def test_deprecated_sqlalchemy_repository_sync_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.repository._sync"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemySyncRepository from 'litestar.contrib.sqlalchemy.repository._sync' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.repository._sync import SQLAlchemySyncRepository


def test_deprecated_sqlalchemy_base_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.base"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="from 'litestar.contrib.sqlalchemy.base' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.base import (
            AuditColumns,
            BigIntAuditBase,
            BigIntBase,
            BigIntPrimaryKey,
            CommonTableAttributes,
            ModelProtocol,
            UUIDAuditBase,
            UUIDBase,
            UUIDPrimaryKey,
            create_registry,
            orm_registry,
            touch_updated_timestamp,
        )


def test_deprecated_sqlalchemy_plugins_init_config_asyncio_handlers() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.asyncio"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing default_before_send_handler from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import default_before_send_handler

    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.asyncio"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing autocommit_before_send_handler from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import autocommit_before_send_handler


def test_deprecated_sqlalchemy_plugins_init_config_sync_handlers() -> None:
    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.sync"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing default_before_send_handler from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.sync import default_before_send_handler

    purge_module(["litestar.contrib.sqlalchemy.plugins.init.config.sync"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing autocommit_before_send_handler from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.plugins.init.config.sync import autocommit_before_send_handler


def test_deprecated_sqlalchemy_repository_util_imports() -> None:
    purge_module(["litestar.contrib.sqlalchemy.repository._util"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing wrap_sqlalchemy_exception from 'litestar.contrib.sqlalchemy.repository._util' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.repository._util import wrap_sqlalchemy_exception

    purge_module(["litestar.contrib.sqlalchemy.repository._util"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing get_instrumented_attr from 'litestar.contrib.sqlalchemy.repository._util' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.repository._util import get_instrumented_attr
