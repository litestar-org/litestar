from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from examples.middleware import session_middleware
from starlite.testing import TestClient


def test_session_middleware_example() -> None:
    with TestClient(app=session_middleware.app) as client:
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
