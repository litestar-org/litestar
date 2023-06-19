from docs.examples.security.using_session_auth import app

from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_401_UNAUTHORIZED
from litestar.testing import TestClient


def test_using_session_auth_signup_flow() -> None:
    with TestClient(app) as client:
        response = client.get("/user")
        assert response.status_code == HTTP_401_UNAUTHORIZED
        response = client.post(
            "/signup", json={"name": "Moishe Zuchmir", "email": "moishe@zuchmir.com", "password": "abcd12345"}
        )
        assert response.status_code == HTTP_201_CREATED
        response = client.get("/user")
        assert response.status_code == HTTP_200_OK


def test_using_session_auth_login_flow() -> None:
    with TestClient(app) as client:
        response = client.post("/login", json={"email": "ludwig@zuchmir.com", "password": "abcd12345"})
        assert response.status_code == HTTP_401_UNAUTHORIZED
        response = client.post(
            "/signup", json={"name": "ludwig Zuchmir", "email": "ludwig@zuchmir.com", "password": "abcd12345"}
        )
        assert response.status_code == HTTP_201_CREATED
        response = client.post("/login", json={"email": "ludwig@zuchmir.com", "password": "abcd12345"})
        assert response.status_code == HTTP_201_CREATED
        response = client.get("/user")
        assert response.status_code == HTTP_200_OK
