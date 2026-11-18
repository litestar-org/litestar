from docs.examples.dependency_injection import dependency_validation_error

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_dependency_value_passed_as_provided() -> None:
    with TestClient(app=dependency_validation_error.app) as client:
        r = client.get("/")
    assert r.status_code == HTTP_200_OK
    assert r.json() == {"hello": "whoops"}
