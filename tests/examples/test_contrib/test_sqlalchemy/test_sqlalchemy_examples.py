import pytest

from litestar.testing import TestClient

pytestmark = pytest.mark.xdist_group("sqlalchemy_examples")


def test_sqlalchemy_declarative_models() -> None:
    from docs.examples.contrib.sqlalchemy.sqlalchemy_declarative_models import app

    with TestClient(app) as client:
        response = client.get("/authors")
        assert response.status_code == 200
        assert len(response.json()) > 0
