from litestar.status_codes import HTTP_201_CREATED
from litestar.testing.client import TestClient


def test_create_underscored_value() -> None:
    from docs.examples.data_transfer_objects.factory.leading_underscore_private import app

    with TestClient(app=app) as client:
        response = client.post("/", json={"bar": "Hello", "_baz": "World!"})

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"bar": "Hello"}
