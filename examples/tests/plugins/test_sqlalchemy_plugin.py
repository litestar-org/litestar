import pytest
from pathlib import Path

from starlite.testing import TestClient


from examples.plugins.sqlalchemy_plugin.sqlalchemy_sync import app as sync_sqla_app
from examples.plugins.sqlalchemy_plugin.sqlalchemy_async import app as async_sqla_app


@pytest.fixture
def clear_sqlite_dbs() -> None:
    yield
    for db_file in Path().glob("*.sqlite"):
        db_file.unlink()


@pytest.mark.parametrize("app", [async_sqla_app, sync_sqla_app])
def test_app(app, clear_sqlite_dbs) -> None:
    with TestClient(app=app) as client:
        create_res = client.post("/companies", json={"name": "my company", "worth": 0.0})
        company_id = create_res.json().get("id")
        assert create_res.status_code == 201
        assert company_id == 1

        get_res = client.get(f"/companies/{company_id}")
        assert get_res.status_code == 200
        assert get_res.json() == {"id": company_id, "name": "my company", "worth": 0.0}
