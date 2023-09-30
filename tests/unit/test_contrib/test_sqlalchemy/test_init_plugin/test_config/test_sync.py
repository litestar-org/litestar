from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine

from litestar.contrib.sqlalchemy.plugins.init.config.sync import SQLAlchemySyncConfig


def test_create_engine_with_engine_instance() -> None:
    engine = create_engine("sqlite:///:memory:")
    config = SQLAlchemySyncConfig(engine_instance=engine)
    with pytest.deprecated_call():
        assert engine is config.create_engine()


def test_create_engine_with_connection_string() -> None:
    config = SQLAlchemySyncConfig(connection_string="sqlite:///:memory:")
    with pytest.deprecated_call():
        engine = config.create_engine()
    assert isinstance(engine, Engine)
