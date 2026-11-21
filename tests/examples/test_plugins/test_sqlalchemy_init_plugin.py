from __future__ import annotations

import pytest
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import StaticPool

from litestar.plugins.sqlalchemy import EngineConfig
from litestar.testing import TestClient

pytestmark = pytest.mark.xdist_group("sqlalchemy_examples")


def test_sync_app(monkeypatch: MonkeyPatch) -> None:
    from docs.examples.plugins.sqlalchemy_init_plugin import sqlalchemy_sync

    engine_config = EngineConfig(connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(sqlalchemy_sync.sqlalchemy_config, "connection_string", "sqlite://")
    monkeypatch.setattr(sqlalchemy_sync.sqlalchemy_config, "engine_config", engine_config)
    with TestClient(app=sqlalchemy_sync.app) as client:
        res = client.get("/sqlalchemy-app")
        assert res.status_code == 200
        assert res.text == "1 2"


def test_async_app(monkeypatch: MonkeyPatch) -> None:
    from docs.examples.plugins.sqlalchemy_init_plugin import sqlalchemy_async

    monkeypatch.setattr(sqlalchemy_async.sqlalchemy_config, "connection_string", "sqlite+aiosqlite://")

    with TestClient(app=sqlalchemy_async.app) as client:
        res = client.get("/sqlalchemy-app")
        assert res.status_code == 200
        assert res.text == "1 2"
