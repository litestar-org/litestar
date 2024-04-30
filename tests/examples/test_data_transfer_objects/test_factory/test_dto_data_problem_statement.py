from unittest.mock import ANY

from litestar.status_codes import HTTP_201_CREATED
from litestar.testing.client import TestClient


def test_create_user(user_data: dict) -> None:
    from docs.examples.data_transfer_objects.factory.dto_data_problem_statement import app

    with TestClient(app=app) as client:
        response = client.post("/users", json=user_data)

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"id": ANY, "name": "Mr Sunglass", "email": "mr.sunglass@example.com", "age": 30}
