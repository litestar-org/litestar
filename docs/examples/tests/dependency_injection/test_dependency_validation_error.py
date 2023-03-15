from examples.dependency_injection import dependency_validation_error
from starlite.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from starlite.testing import TestClient


def test_route_returns_internal_server_error() -> None:
    with TestClient(app=dependency_validation_error.app) as client:
        r = client.get("/")
    assert r.status_code == HTTP_500_INTERNAL_SERVER_ERROR
