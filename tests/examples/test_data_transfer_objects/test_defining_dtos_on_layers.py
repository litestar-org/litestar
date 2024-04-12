from unittest.mock import ANY

from docs.examples.data_transfer_objects.defining_dtos_on_layers import app

from litestar.testing.client.sync_client import TestClient

app.debug = True


def test_create_user(user_data: dict) -> None:
    with TestClient(app=app) as client:
        response = client.post("/", json=user_data)

    assert response.json() == {"id": ANY, "name": "Mr Sunglass", "email": "mr.sunglass@example.com", "age": 30}


def test_get_users() -> None:
    with TestClient(app=app) as client:
        response = client.get("/")

    assert response.json() == [{"id": ANY, "name": "Mr Sunglass", "email": "mr.sunglass@example.com", "age": 30}]


def test_get_user() -> None:
    with TestClient(app=app) as client:
        response = client.get("a3cad591-5b01-4341-ae8f-94f78f790674")

    assert response.json() == {
        "id": "a3cad591-5b01-4341-ae8f-94f78f790674",
        "name": "Mr Sunglass",
        "email": "mr.sunglass@example.com",
        "age": 30,
    }


def test_update_user(user_data: dict) -> None:
    with TestClient(app=app) as client:
        response = client.put("/a3cad591-5b01-4341-ae8f-94f78f790674", json=user_data)

    assert response.json() == {"id": ANY, "name": "Mr Sunglass", "email": "mr.sunglass@example.com", "age": 30}


def test_delete_user() -> None:
    with TestClient(app=app) as client:
        response = client.delete("/a3cad591-5b01-4341-ae8f-94f78f790674")

    assert response.content == b""