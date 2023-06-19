from docs.examples.middleware.rate_limit import app

from litestar.status_codes import HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS
from litestar.testing import TestClient


def test_rate_limit_middleware_example() -> None:
    with TestClient(app=app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "ok"

        response = client.get("/")
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
