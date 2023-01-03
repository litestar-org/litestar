from starlite import TestClient
from examples.lifecycle_hooks.layered_hooks import app as layered_hooks_app


def test_layered_hooks() -> None:
    with TestClient(app=layered_hooks_app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.text == "app after request"

        res = client.get("/override")
        assert res.status_code == 200
        assert res.text == "handler after request"
