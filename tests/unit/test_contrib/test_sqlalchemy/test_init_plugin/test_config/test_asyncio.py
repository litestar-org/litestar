from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import SQLAlchemyAsyncConfig


def test_create_engine_with_engine_instance() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    config = SQLAlchemyAsyncConfig(engine_instance=engine)
    with pytest.deprecated_call():
        assert engine is config.create_engine()


def test_create_engine_with_connection_string() -> None:
    config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///:memory:")
    with pytest.deprecated_call():
        engine = config.create_engine()
    assert isinstance(engine, AsyncEngine)
