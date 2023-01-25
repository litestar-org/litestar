from examples.parameters.header_and_cookie_parameters import app
from starlite import TestClient
from starlite.status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
)


def test_header_and_cookie_parameters() -> None:
    with TestClient(app=app) as client:
        assert client.get("/users/1").status_code == HTTP_400_BAD_REQUEST
        assert (
            client.get("/users/1", headers={"X-API-KEY": "foo"}, cookies={"my-cookie-param": "bar"}).status_code
            == HTTP_401_UNAUTHORIZED
        )
        res = client.get(
            "/users/1", headers={"X-API-KEY": "super-secret-secret"}, cookies={"my-cookie-param": "cookie-secret"}
        )
        assert res.status_code == HTTP_200_OK
        assert res.json() == {"id": 1, "name": "John Doe"}
