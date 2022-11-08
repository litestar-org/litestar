from examples.responses.response_cookies_1 import app
from starlite import TestClient


def test_response_cookies() -> None:
    with TestClient(app=app) as client:
        res = client.get("/router-path/controller-path")
        assert res.status_code == 200
        assert res.cookies["local-cookie"] == '"local value"'
        assert res.cookies["controller-cookie"] == '"controller value"'
        assert res.cookies["router-cookie"] == '"router value"'
        assert res.cookies["app-cookie"] == '"app value"'
