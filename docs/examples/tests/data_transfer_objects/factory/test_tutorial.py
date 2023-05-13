from __future__ import annotations

from litestar.testing.client import TestClient


def test_initial_pattern_app():
    from docs.examples.data_transfer_objects.factory.tutorial.initial_pattern import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {"name": "peter", "age": 30, "email": "email_of_peter@example.com"}


def test_simple_dto_exclude():
    from docs.examples.data_transfer_objects.factory.tutorial.simple_dto_exclude import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {"name": "peter", "age": 30}


def test_nested_exclude():
    from docs.examples.data_transfer_objects.factory.tutorial.nested_exclude import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {"name": "peter", "age": 30, "address": {"city": "Cityville", "country": "Countryland"}}


def test_nested_collection_exclude():
    from docs.examples.data_transfer_objects.factory.tutorial.nested_collection_exclude import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {
        "name": "peter",
        "age": 30,
        "address": {"city": "Cityville", "country": "Countryland"},
        "children": [{"name": "Child1", "age": 10}, {"name": "Child2", "age": 8}],
    }


def test_max_nested_depth():
    from docs.examples.data_transfer_objects.factory.tutorial.max_nested_depth import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {
        "name": "peter",
        "age": 30,
        "address": {"city": "Cityville", "country": "Countryland"},
        "children": [{"name": "Child1", "age": 10, "children": []}, {"name": "Child2", "age": 8, "children": []}],
    }


def test_explicit_field_renaming():
    from docs.examples.data_transfer_objects.factory.tutorial.explicit_field_renaming import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {
        "name": "peter",
        "age": 30,
        "location": {"city": "Cityville", "country": "Countryland"},
        "children": [{"name": "Child1", "age": 10}, {"name": "Child2", "age": 8}],
    }


def test_field_renaming_strategy():
    from docs.examples.data_transfer_objects.factory.tutorial.field_renaming_strategy import app

    with TestClient(app=app) as client:
        response = client.get("/person/peter")
    assert response.status_code == 200
    assert response.json() == {
        "NAME": "peter",
        "AGE": 30,
        "ADDRESS": {"CITY": "Cityville", "COUNTRY": "Countryland"},
        "CHILDREN": [{"NAME": "Child1", "AGE": 10}, {"NAME": "Child2", "AGE": 8}],
    }


def test_simple_receiving_data():
    from docs.examples.data_transfer_objects.factory.tutorial.simple_receiving_data import app

    with TestClient(app=app) as client:
        response = client.post("/person", json={"name": "peter", "age": 40, "email": "email_of_peter@example.com"})
    assert response.status_code == 201
    assert response.json() == {"name": "peter", "age": 40}
