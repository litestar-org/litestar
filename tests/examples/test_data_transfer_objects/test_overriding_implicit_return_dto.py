from litestar.status_codes import HTTP_201_CREATED
from litestar.testing.client import TestClient


def test_create_user(user_data: dict) -> None:
    from docs.examples.data_transfer_objects.overriding_implicit_return_dto import app

    with TestClient(app=app) as client:
        response = client.post("/", json=user_data)

    assert response.status_code == HTTP_201_CREATED
    assert response.content == b"Mr Sunglass"
