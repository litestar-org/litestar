from docs.examples.parameters.header_and_cookie_parameters import app

from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
)
from litestar.testing import TestClient


def test_header_and_cookie_parameters() -> None:
    with TestClient(app=app) as client:
        response = client.get("/users/1")
        assert response.status_code == HTTP_400_BAD_REQUEST
        client.cookies["my-cookie-param"] = "bar"

        response = client.get("/users/1", headers={"X-API-KEY": "foo"})
        assert response.status_code == HTTP_401_UNAUTHORIZED
        client.cookies["my-cookie-param"] = "cookie-secret"

        response = client.get("/users/1", headers={"X-API-KEY": "super-secret-secret"})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"id": 1, "name": "John Doe"}
