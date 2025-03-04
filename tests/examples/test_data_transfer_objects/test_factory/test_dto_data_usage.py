from unittest.mock import ANY

from litestar.testing import TestClient


def test_create_user(user_data) -> None:
    from docs.examples.data_transfer_objects.factory.dto_data_usage import app

    with TestClient(app) as client:
        response = client.post("/users", json=user_data)

    assert response.status_code == 201
    assert response.json() == {"id": ANY, "name": "Mr Sunglass", "email": "mr.sunglass@example.com", "age": 30}
