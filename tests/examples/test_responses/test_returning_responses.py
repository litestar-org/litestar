from docs.examples.responses.returning_responses import app

from litestar.testing import TestClient


def test_returning_responses() -> None:
    with TestClient(app=app) as client:
        res = client.get("/resources")
        assert res.headers["MY-HEADER"] == "xyz"
        assert res.cookies["my-cookie"] == "abc"
        assert res.json() == {"id": 1, "name": "my resource"}
