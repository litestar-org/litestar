from examples.responses.response_cookies_2 import app
from starlite import TestClient


def test_response_cookies() -> None:
    with TestClient(app=app) as client:
        res = client.get("/controller-path")
        assert res.status_code == 200
        assert res.cookies["my-cookie"] == "456"
