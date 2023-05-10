from __future__ import annotations

from litestar.testing.client import TestClient


def test_initial_pattern_app():
    from docs.examples.data_transfer_objects.factory.tutorial.initial_pattern import app

    data = {"name": "John Doe", "age": 30, "email": "johndoe@example.com"}
    with TestClient(app=app) as client:
        response = client.post("/create-person", json=data)
    assert response.status_code == 201
    assert response.json() == data


def test_simple_dto_example():
    from docs.examples.data_transfer_objects.factory.tutorial.simple_dto_example import app

    with TestClient(app=app) as client:
        response = client.get("/person/John%20Doe")
    assert response.status_code == 200
    assert response.json() == {"name": "John Doe", "age": 30}
