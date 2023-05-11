from __future__ import annotations

from unittest.mock import ANY

from litestar.testing import TestClient


def test_dto_data_problem_statement_app() -> None:
    from docs.examples.data_transfer_objects.factory.dto_data_problem_statement import app

    with TestClient(app) as client:
        response = client.post("/person", json={"name": "John", "age": 30})
        assert response.status_code == 500
        assert "missing 1 required positional argument: 'id'" in response.json()["detail"]


def test_dto_data_usage_app() -> None:
    from docs.examples.data_transfer_objects.factory.dto_data_usage import app

    with TestClient(app) as client:
        response = client.post("/person", json={"name": "John", "age": 30})
        assert response.status_code == 201
        assert response.json() == {"id": ANY, "name": "John", "age": 30}
