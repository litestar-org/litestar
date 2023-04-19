import pytest

from .get_list import (
    dataclass as dataclass_app,
    dict as dict_app,
    query_param,
    query_param_default,
    query_param_validate,
    query_param_validate_manually,
)

from litestar.testing import TestClient
from msgspec import to_builtins


@pytest.mark.parametrize("module", [dataclass_app, dict_app, query_param_default])
def test_get_list_dataclass(module) -> None:
    with TestClient(module.app) as client:
        res = client.get("/")

        assert res.status_code == 200
        assert res.json() == to_builtins(module.TODO_LIST)


@pytest.mark.parametrize("module", [query_param, query_param_validate_manually])
def test_get_list_query_param(module) -> None:
    with TestClient(module.app) as client:
        res = client.get("/?done=true")

        assert res.status_code == 200
        assert res.json() == to_builtins([i for i in module.TODO_LIST if i.done])
