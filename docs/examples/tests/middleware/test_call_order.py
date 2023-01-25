from examples.middleware.call_order import app
from starlite import TestClient


def test_call_order() -> None:
    with TestClient(app=app) as client:
        res = client.get("/router/controller/handler")
        assert res.status_code == 200
        assert res.json() == [0, 1, 2, 3, 4, 5, 6, 7]
