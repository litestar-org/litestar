from __future__ import annotations

from unittest.mock import ANY

from litestar.testing import TestClient


def test_dto_data_problem_statement_app() -> None:
    from docs.examples.data_transfer_objects.factory.dto_data_problem_statement import app

    with TestClient(app) as client:
        response = client.post("/person", json={"name": "John", "age": 30})
        assert response.status_code == 500


def test_dto_data_usage_app() -> None:
    from docs.examples.data_transfer_objects.factory.dto_data_usage import app

    with TestClient(app) as client:
        response = client.post("/person", json={"name": "John", "age": 30})
        assert response.status_code == 201
        assert response.json() == {"id": ANY, "name": "John", "age": 30}


def test_dto_data_nested_data_create_instance_app() -> None:
    from docs.examples.data_transfer_objects.factory.providing_values_for_nested_data import app

    with TestClient(app) as client:
        response = client.post(
            "/person",
            json={
                "name": "John",
                "age": 30,
                "address": {"street": "Fake Street"},
            },
        )
        assert response.status_code == 201
        assert response.json() == {
            "id": 1,
            "name": "John",
            "age": 30,
            "address": {"id": 2, "street": "Fake Street"},
        }


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


def test_exclude_fields_app() -> None:
    from docs.examples.data_transfer_objects.factory.excluding_fields import app

    with TestClient(app) as client:
        response = client.post(
            "/users",
            json={"name": "Litestar User", "password": "xyz", "created_at": "2023-04-24T00:00:00Z"},
        )
        assert response.status_code == 201
        assert response.json() == {
            "created_at": "0001-01-01T00:00:00",
            "address": {"city": "Anytown", "state": "NY", "zip": "12345"},
            "pets": [{"name": "Fido"}, {"name": "Spot"}],
            "name": "Litestar User",
        }


def test_include_fields_app() -> None:
    from docs.examples.data_transfer_objects.factory.included_fields import app

    with TestClient(app) as client:
        response = client.post(
            "/users",
            json={"name": "Litestar User", "password": "xyz", "created_at": "2023-04-24T00:00:00Z"},
        )
        assert response.status_code == 201
        assert response.json() == {
            "address": {"street": "123 Main St"},
            "pets": [{"name": "Fido"}, {"name": "Spot"}],
        }


def test_enveloped_return_data_app() -> None:
    from docs.examples.data_transfer_objects.factory.enveloping_return_data import app

    with TestClient(app) as client:
        response = client.get("/users")
        assert response.status_code == 200
        assert response.json() == {
            "count": 1,
            "data": [{"id": 1, "name": "Litestar User"}],
        }


def test_paginated_return_data_app() -> None:
    from docs.examples.data_transfer_objects.factory.paginated_return_data import app

    with TestClient(app) as client:
        response = client.get("/users")
        assert response.status_code == 200
        assert response.json() == {
            "page_size": 10,
            "total_pages": 1,
            "current_page": 1,
            "items": [{"id": 1, "name": "Litestar User"}],
        }


def test_response_return_data_app() -> None:
    from docs.examples.data_transfer_objects.factory.response_return_data import app

    with TestClient(app) as client:
        response = client.get("/users")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "Litestar User"}
        assert response.headers["X-Total-Count"] == "1"
