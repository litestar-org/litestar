from examples.responses.response_headers_1 import app
from starlite import TestClient


def test_response_headers() -> None:
    with TestClient(app=app) as client:
        res = client.get("/router-path/controller-path/handler-path")
        assert res.status_code == 200
        assert res.headers["my-local-header"] == "local header"
        assert res.headers["controller-level-header"] == "controller header"
        assert res.headers["router-level-header"] == "router header"
        assert res.headers["app-level-header"] == "app header"
