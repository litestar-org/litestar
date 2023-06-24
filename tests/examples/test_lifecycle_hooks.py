from docs.examples.lifecycle_hooks.after_request import app as after_request_app
from docs.examples.lifecycle_hooks.after_response import app as after_response_app
from docs.examples.lifecycle_hooks.before_request import app as before_request_app
from docs.examples.lifecycle_hooks.layered_hooks import app as layered_hooks_app

from litestar.testing import TestClient


def test_layered_hooks() -> None:
    with TestClient(app=layered_hooks_app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.text == "app after request"

        res = client.get("/override")
        assert res.status_code == 200
        assert res.text == "handler after request"


def test_before_request_app() -> None:
    with TestClient(app=before_request_app) as client:
        res = client.get("/", params={"name": "Luke"})
        assert res.status_code == 200
        assert res.json() == {"message": "Use the handler, Luke"}

        res = client.get("/", params={"name": "Ben"})
        assert res.status_code == 200
        assert res.json() == {"message": "These are not the bytes you are looking for"}


def test_after_request_app() -> None:
    with TestClient(app=after_request_app) as client:
        res = client.get("/hello")
        assert res.status_code == 200
        assert res.json() == {"message": "Hello, world"}

        res = client.get("/goodbye")
        assert res.status_code == 200
        assert res.json() == {"message": "Goodbye"}


def test_after_response_app() -> None:
    with TestClient(app=after_response_app) as client:
        res = client.get("/hello")
        assert res.status_code == 200
        assert res.json() == {}

        res = client.get("/hello")
        assert res.status_code == 200
        assert res.json() == {"/hello": 1}
