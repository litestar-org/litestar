from uuid import uuid4

from docs.examples.security.jwt.using_oauth2_password_bearer import app

from litestar.status_codes import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED
from litestar.testing import TestClient


def test_using_oauth2_password_bearer_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/some-path")
        assert response.status_code == HTTP_401_UNAUTHORIZED
        response = client.post(
            "/login", json={"name": "Moishe Zuchmir", "email": "moishe@zuchmir.com", "id": str(uuid4())}
        )
        assert response.status_code == HTTP_201_CREATED, response.json()
