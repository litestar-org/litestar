from __future__ import annotations

from litestar.testing.client import TestClient


def test_initial_pattern_app():
    from docs.examples.data_transfer_objects.factory.tutorial.initial_pattern import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {"name": "peter", "age": 30, "email": "email_of_peter@example.com"}


def test_simple_dto_example():
    from docs.examples.data_transfer_objects.factory.tutorial.simple_dto_example import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {"name": "peter", "age": 30}
