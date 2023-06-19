from docs.examples.middleware.call_order import app

from litestar.testing import TestClient


def test_call_order() -> None:
    with TestClient(app=app) as client:
        response = client.get("/router/controller/handler")
        assert response.status_code == 200
        assert response.json() == [0, 1, 2, 3, 4, 5, 6, 7]
