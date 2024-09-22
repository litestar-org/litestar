from __future__ import annotations

import pytest
from advanced_alchemy import repository as advanced_alchemy_repo
from advanced_alchemy import types as advanced_alchemy_types
from advanced_alchemy.repository import typing as advanced_alchemy_typing
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import SQLAlchemyAsyncConfig
from litestar.contrib.sqlalchemy.plugins.init.config.sync import SQLAlchemySyncConfig


def test_create_engine_with_engine_instance() -> None:
    engine = create_engine("sqlite:///:memory:")
    config = SQLAlchemySyncConfig(engine_instance=engine)
    with pytest.deprecated_call():
        assert engine is config.create_engine()  # type: ignore[attr-defined]


def test_create_engine_with_connection_string() -> None:
    config = SQLAlchemySyncConfig(connection_string="sqlite:///:memory:")
    with pytest.deprecated_call():
        engine = config.create_engine()  # type: ignore[attr-defined]
    assert isinstance(engine, Engine)


def test_async_create_engine_with_engine_instance() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    config = SQLAlchemyAsyncConfig(engine_instance=engine)
    with pytest.deprecated_call():
        assert engine is config.create_engine()  # type: ignore[attr-defined]


def test_async_create_engine_with_connection_string() -> None:
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


def test_deprecated_sqlalchemy_imports() -> None:
    with pytest.warns(
        DeprecationWarning, match="importing SQLAlchemyAsyncRepository from 'litestar.contrib.sqlalchemy' is deprecated"
    ):
        pass

    with pytest.warns(
        DeprecationWarning, match="importing SQLAlchemySyncRepository from 'litestar.contrib.sqlalchemy' is deprecated"
    ):
        pass

    with pytest.warns(DeprecationWarning, match="importing ModelT from 'litestar.contrib.sqlalchemy' is deprecated"):
        pass

    with pytest.warns(
        DeprecationWarning, match="importing wrap_sqlalchemy_exception from 'litestar.contrib.sqlalchemy' is deprecated"
    ):
        pass


def test_deprecated_sqlalchemy_plugins_imports() -> None:
    with pytest.warns(
        DeprecationWarning,
        match="importing AsyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning, match="importing EngineConfig from 'litestar.contrib.sqlalchemy.plugins' is deprecated"
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing GenericSQLAlchemyConfig from 'litestar.contrib.sqlalchemy.plugins' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncConfig from 'litestar.contrib.sqlalchemy.plugins' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyInitPlugin from 'litestar.contrib.sqlalchemy.plugins' is deprecated",
    ):
        pass


def test_deprecated_sqlalchemy_plugins_init_imports() -> None:
    with pytest.warns(
        DeprecationWarning,
        match="importing AsyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning, match="importing EngineConfig from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated"
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing GenericSQLAlchemyConfig from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncConfig from 'litestar.contrib.sqlalchemy.plugins.init' is deprecated",
    ):
        pass


def test_deprecated_sqlalchemy_plugins_init_config_imports() -> None:
    with pytest.warns(
        DeprecationWarning,
        match="importing AsyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins.init.config' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing EngineConfig from 'litestar.contrib.sqlalchemy.plugins.init.config' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing GenericSQLAlchemyConfig from 'litestar.contrib.sqlalchemy.plugins.init.config' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config' is deprecated",
    ):
        pass


def test_deprecated_sqlalchemy_plugins_init_config_common_imports() -> None:
    with pytest.warns(
        DeprecationWarning,
        match="importing SESSION_SCOPE_KEY from 'litestar.contrib.sqlalchemy.plugins.init.config.common' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing SESSION_TERMINUS_ASGI_EVENTS from 'litestar.contrib.sqlalchemy.plugins.init.config.common' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing GenericSQLAlchemyConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.common' is deprecated",
    ):
        pass


def test_deprecated_sqlalchemy_plugins_init_config_sync_imports() -> None:
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemySyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing AlembicSyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing SyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.sync' is deprecated",
    ):
        pass


def test_deprecated_sqlalchemy_plugins_init_config_asyncio_imports() -> None:
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing AlembicAsyncConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated",
    ):
        pass

    with pytest.warns(
        DeprecationWarning,
        match="importing AsyncSessionConfig from 'litestar.contrib.sqlalchemy.plugins.init.config.asyncio' is deprecated",
    ):
        pass
