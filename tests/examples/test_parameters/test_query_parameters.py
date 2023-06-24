from docs.examples.parameters.query_params import app as query_params_app
from docs.examples.parameters.query_params_constraints import (
    app as query_params_constraints_app,
)
from docs.examples.parameters.query_params_default import app as query_params_default_app
from docs.examples.parameters.query_params_optional import app as query_params_optional_app
from docs.examples.parameters.query_params_remap import app as query_params_remap_app
from docs.examples.parameters.query_params_types import app as query_params_types_app

from litestar.testing import TestClient


def test_query_params() -> None:
    with TestClient(app=query_params_app) as client:
        res = client.get("/?param=hello")
        assert res.status_code == 200
        assert res.json() == {"param": "hello"}


def test_query_params_default() -> None:
    with TestClient(app=query_params_default_app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"param": "hello"}

        res = client.get("/?param=world")
        assert res.status_code == 200
        assert res.json() == {"param": "world"}


def test_query_params_optional() -> None:
    with TestClient(app=query_params_optional_app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"param": None}

        res = client.get("/?param=world")
        assert res.status_code == 200
        assert res.json() == {"param": "world"}


def test_query_params_types() -> None:
    with TestClient(app=query_params_types_app) as client:
        res = client.get("/?date=2022-11-28T13:22:06.916540&floating_number=0.1&number=42&strings=1&strings=2")
        assert res.status_code == 200, res.json()
        assert res.json() == {"datetime": "2022-11-29T13:22:06.916540", "int": 42, "float": 0.1, "list": ["1", "2"]}


def test_query_params_remap() -> None:
    with TestClient(app=query_params_remap_app) as client:
        res = client.get("/?camelCase=hello")
        assert res.status_code == 200
        assert res.json() == {"param": "hello"}


def test_query_params_constraint() -> None:
    with TestClient(app=query_params_constraints_app) as client:
        res = client.get("/?param=1")
        assert res.status_code == 400

        res = client.get("/?param=6")
        assert res.status_code == 200
        assert res.json() == {"param": 6}
