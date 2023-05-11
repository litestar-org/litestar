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


def test_patch_requests_app() -> None:
    from docs.examples.data_transfer_objects.factory.patch_requests import app

    with TestClient(app) as client:
        response = client.patch(
            "/person/f32ff2ce-e32f-4537-9dc0-26e7599f1380",
            json={"name": "Peter Pan"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "id": "f32ff2ce-e32f-4537-9dc0-26e7599f1380",
            "name": "Peter Pan",
            "age": 40,
        }
