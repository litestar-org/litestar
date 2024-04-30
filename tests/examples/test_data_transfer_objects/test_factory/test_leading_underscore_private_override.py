import pytest

from litestar.status_codes import HTTP_201_CREATED
from litestar.testing.client import TestClient


@pytest.mark.xdist_group(name="doc-examples")
def test_create_underscored_field() -> None:
    from docs.examples.data_transfer_objects.factory.leading_underscore_private_override import app

    with TestClient(app=app) as client:
        response = client.post("/", json={"bar": "Hello", "_baz": "World!"})

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"bar": "Hello", "_baz": "World!"}
