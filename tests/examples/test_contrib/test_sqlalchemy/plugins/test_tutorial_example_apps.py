from __future__ import annotations

from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch
from docs.examples.contrib.sqlalchemy.plugins.tutorial import (
    full_app_no_plugins,
    full_app_with_init_plugin,
    full_app_with_plugin,
    full_app_with_serialization_plugin,
    full_app_with_session_di,
)
from sqlalchemy.ext.asyncio import create_async_engine

from litestar.testing import TestClient


@pytest.mark.parametrize(
    "app_module",
    [
        full_app_no_plugins,
        full_app_with_init_plugin,
        full_app_with_plugin,
        full_app_with_serialization_plugin,
        full_app_with_session_di,
    ],
)
async def test_tutorial_example_apps(monkeypatch: MonkeyPatch, app_module: Any) -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(app_module.Base.metadata.create_all)

    try:
        monkeypatch.setattr(app_module, "create_async_engine", lambda *a, **kw: engine)
    except AttributeError:
        app_module.db_config.connection_string = None
        app_module.db_config.engine_instance = engine

    todo = {"title": "Start writing todo list", "done": True}
    todo_list = [todo]

    with TestClient(app_module.app) as client:
        response = client.post("/", json=todo)
        assert response.status_code == 201
        assert response.json() == todo

        response = client.post("/", json=todo)
        assert response.status_code == 409

        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == todo_list

        response = client.get("/?done=false")
        assert response.status_code == 200
        assert response.json() == []

        response = client.put("/Start writing another list", json=todo)
        assert response.status_code == 404

        updated_todo = dict(todo)
        updated_todo["done"] = False
        response = client.put("/Start writing todo list", json=updated_todo)
        assert response.status_code == 200
        assert response.json() == updated_todo
