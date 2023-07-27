from __future__ import annotations

from typing import Any

import pytest

from litestar.testing import TestClient

pytestmark = pytest.mark.xdist_group("sqla-plugin-examples")


@pytest.fixture
def data() -> list[dict[str, Any]]:
    return [{"title": "test", "done": False}]


def test_sqlalchemy_async_plugin_example(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_async_plugin_example import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data


def test_sqlalchemy_sync_plugin_example(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_sync_plugin_example import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data


def test_sqlalchemy_async_init_plugin_example(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_async_init_plugin_example import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data


def test_sqlalchemy_sync_init_plugin_example(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_sync_init_plugin_example import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data


def test_sqlalchemy_async_init_plugin_dependencies() -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_async_dependencies import app

    with TestClient(app) as client:
        assert client.post("/").json() == [1, 2]


def test_sqlalchemy_sync_init_plugin_dependencies() -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_sync_dependencies import app

    with TestClient(app) as client:
        assert client.post("/").json() == [1, 2]


def test_sqlalchemy_async_before_send_handler() -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_async_before_send_handler import app

    from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import autocommit_before_send_handler

    assert autocommit_before_send_handler is app.before_send[0].ref.value


def test_sqlalchemy_sync_before_send_handler() -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_sync_before_send_handler import app

    from litestar.contrib.sqlalchemy.plugins.init.config.sync import autocommit_before_send_handler

    assert autocommit_before_send_handler is app.before_send[0].ref.value.func


def test_sqlalchemy_async_serialization_plugin(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_async_serialization_plugin import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data


def test_sqlalchemy_sync_serialization_plugin(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_sync_serialization_plugin import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data


def test_sqlalchemy_async_serialization_dto(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_async_serialization_dto import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data


def test_sqlalchemy_async_serialization_plugin_marking_fields(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_async_serialization_plugin_marking_fields import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data


def test_sqlalchemy_sync_serialization_plugin_marking_fields(data: dict[str, Any]) -> None:
    from docs.examples.contrib.sqlalchemy.plugins.sqlalchemy_sync_serialization_plugin_marking_fields import app

    with TestClient(app) as client:
        assert client.post("/", json=data[0]).json() == data
