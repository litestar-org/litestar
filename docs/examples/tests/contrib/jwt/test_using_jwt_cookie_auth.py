from uuid import uuid4

from examples.contrib.jwt.using_jwt_cookie_auth import app
from starlite.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_401_UNAUTHORIZED
from starlite.testing import TestClient


def test_using_jwt_cookie_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/some-path")
        assert response.status_code == HTTP_401_UNAUTHORIZED
        response = client.post(
            "/login", json={"name": "Moishe Zuchmir", "email": "moishe@zuchmir.com", "id": str(uuid4())}
        )
        assert response.status_code == HTTP_201_CREATED, response.json()
        response = client.get("/some-path")
        assert response.status_code == HTTP_200_OK
