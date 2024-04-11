from unittest.mock import ANY

from docs.examples.data_transfer_objects.defining_dtos_on_layers import UserController

from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from litestar.testing import create_test_client


def test_create_user(user_data: dict) -> None:
    with create_test_client(UserController) as client:
        response = client.post("/", json=user_data)

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"id": "a3cad591-5b01-4341-ae8f-94f78f790674", "name": "Litestar User"}


def test_get_users() -> None:
    with create_test_client(UserController) as client:
        response = client.get("/")

    assert response.status_code == HTTP_200_OK
    assert response.json() == [{"id": ANY, "name": "Litestar User"}]


def test_get_user() -> None:
    with create_test_client(UserController) as client:
        response = client.get("a3cad591-5b01-4341-ae8f-94f78f790674")

    assert response.status_code == HTTP_200_OK
    assert response.json() == {"id": "a3cad591-5b01-4341-ae8f-94f78f790674", "name": "Litestar User"}


def test_update_user(user_data: dict) -> None:
    with create_test_client(UserController) as client:
        response = client.put("/a3cad591-5b01-4341-ae8f-94f78f790674", json=user_data)

    assert response.status_code == HTTP_200_OK
    assert response.json() == {"id": "a3cad591-5b01-4341-ae8f-94f78f790674", "name": "Litestar User"}


def test_delete_user() -> None:
    with create_test_client(UserController) as client:
        response = client.delete("/a3cad591-5b01-4341-ae8f-94f78f790674")

    assert response.status_code == HTTP_204_NO_CONTENT
    assert response.content == b""
