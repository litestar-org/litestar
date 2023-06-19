from docs.examples.middleware.session.cookies_full_example import app

from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from litestar.testing import TestClient


def test_session_middleware_example() -> None:
    with TestClient(app=app) as client:
        response = client.get("/session")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"has_session": False}

        response = client.post("/session")
        assert response.status_code == HTTP_201_CREATED

        response = client.get("/session")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"has_session": True}

        response = client.delete("/session")
        assert response.status_code == HTTP_204_NO_CONTENT

        response = client.get("/session")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"has_session": False}
