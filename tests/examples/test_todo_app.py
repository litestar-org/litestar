from typing import Any

import pytest
from docs.examples.todo_app import full_app
from docs.examples.todo_app import update as update_app
from docs.examples.todo_app.create import dataclass as dataclass_create_app
from docs.examples.todo_app.create import dict as dict_create_app
from docs.examples.todo_app.get_list import dataclass as get_dataclass_app
from docs.examples.todo_app.get_list import dict as get_dict_app
from docs.examples.todo_app.get_list import (
    query_param,
    query_param_default,
    query_param_validate,
    query_param_validate_manually,
)
from msgspec import to_builtins

from litestar.testing import TestClient


@pytest.mark.parametrize("module", [update_app, full_app])
def test_update(module: Any) -> None:
    with TestClient(module.app) as client:
        res = client.put("/Profit", json={"title": "Profit", "done": True})

        assert res.status_code == 200
        assert module.TODO_LIST[2].done
        assert res.json() == to_builtins(module.TODO_LIST)


@pytest.mark.parametrize("module", [get_dataclass_app, get_dict_app, query_param_default])
def test_get_list_dataclass(module) -> None:
    with TestClient(module.app) as client:
        res = client.get("/")

        assert res.status_code == 200
        assert res.json() == to_builtins(module.TODO_LIST)


@pytest.mark.parametrize("module", [query_param, query_param_validate_manually, query_param_validate])
def test_get_list_query_param(module) -> None:
    with TestClient(module.app) as client:
        res = client.get("/?done=1")

        assert res.status_code == 200
        assert res.json() == to_builtins([i for i in module.TODO_LIST if i.done])


@pytest.mark.parametrize("module", [query_param_validate_manually, query_param_validate, full_app])
def test_get_list_query_param_invalid(module) -> None:
    with TestClient(module.app) as client:
        res = client.get("/?done=john")

        assert res.status_code == 400


def test_dict_create() -> None:
    with TestClient(dict_create_app.app) as client:
        res = client.post("/", json={"title": "foo", "done": True})

        assert res.status_code == 201
        assert res.json() == [{"title": "foo", "done": True}]
        assert [{"title": "foo", "done": True}] == dict_create_app.TODO_LIST


@pytest.mark.parametrize("module", [dataclass_create_app, full_app])
def test_dataclass_create(module: Any) -> None:
    with TestClient(module.app) as client:
        res = client.post("/", json={"title": "foo", "done": True})

        assert res.status_code == 201
        assert res.json() == to_builtins(module.TODO_LIST)
        assert len(module.TODO_LIST)
        assert module.TODO_LIST[-1] == module.TodoItem(title="foo", done=True)
