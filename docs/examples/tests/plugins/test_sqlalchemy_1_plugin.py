from pathlib import Path
from typing import Generator

import pytest

from examples.plugins.sqlalchemy_1_plugin.sqlalchemy_async import app as async_sqla_app
from examples.plugins.sqlalchemy_1_plugin.sqlalchemy_relationships import (
    app as relationship_app,
)
from examples.plugins.sqlalchemy_1_plugin.sqlalchemy_relationships_to_many import (
    app as relationship_app_to_many,
)
from examples.plugins.sqlalchemy_1_plugin.sqlalchemy_sync import app as sync_sqla_app
from starlite import Starlite
from starlite.testing import TestClient


@pytest.fixture(autouse=True)
def clear_sqlite_dbs() -> Generator[None, None, None]:
    yield
    for db_file in Path().glob("*.sqlite"):
        db_file.unlink()


@pytest.mark.parametrize("app", [async_sqla_app, sync_sqla_app])
def test_app(app: Starlite) -> None:
    with TestClient(app=app) as client:
        assert client.get("/companies/1").status_code == 404

        create_res = client.post("/companies", json={"name": "my company", "worth": 0.0})
        company_id = create_res.json().get("id")
        assert create_res.status_code == 201
        assert company_id == 1

        get_res = client.get(f"/companies/{company_id}")
        assert get_res.status_code == 200
        assert get_res.json() == {"id": company_id, "name": "my company", "worth": 0.0}


def test_relationships() -> None:
    with TestClient(app=relationship_app) as client:
        assert client.get("/user/2").status_code == 404

        res = client.get("/user/1")
        assert res.status_code == 200
        assert res.json() == {
            "id": 1,
            "name": "Peter",
            "company_id": 1,
            "company": {"id": 1, "name": "Peter Co.", "worth": 0.0},
        }


def test_relationships_to_many() -> None:
    with TestClient(app=relationship_app_to_many) as client:
        assert client.get("/user/2").status_code == 404

        res = client.get("/user/1")
        assert res.status_code == 200
        assert res.json() == {"id": 1, "name": "Peter", "pets": [{"id": 1, "name": "Paul"}]}
