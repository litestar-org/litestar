from examples.routing import mounting
from starlite.status_codes import HTTP_200_OK
from starlite.testing import TestClient


def test_mounting_example() -> None:
    with TestClient(mounting.app) as client:
        response = client.get("/some/sub-path")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"forwarded_path": "/"}

        response = client.get("/some/sub-path/123")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"forwarded_path": "/123"}

        response = client.get("/some/sub-path/123/another/sub-path/456")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"forwarded_path": "/123/another/sub-path/456"}
