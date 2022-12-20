from starlite import TestClient
from examples.responses.custom_responses import app as app_1


def test_custom_responses() -> None:
    with TestClient(app=app_1) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"foo": ["bar", "baz"]}
