from docs.examples.exceptions import (
    layered_handlers,
    override_default_handler,
    per_exception_handlers,
)

from litestar.testing import TestClient


def test_override_default_handler() -> None:
    with TestClient(app=override_default_handler.app) as client:
        res = client.get("/")
        assert res.status_code == 400
        assert res.text == "an error occurred"


def test_per_exception_handlers() -> None:
    with TestClient(app=per_exception_handlers.app) as client:
        res = client.get("/validation-error")
        assert res.status_code == 400
        assert res.text.startswith("validation error:")

        res = client.get("/server-error")
        assert res.status_code == 500
        assert res.text == "server error: 500: Internal Server Error"

        res = client.get("/value-error")
        assert res.status_code == 400
        assert res.text == "value error: this is wrong"


def test_layered_handlers() -> None:
    with TestClient(app=layered_handlers.app) as client:
        res = client.get("/")
        assert res.status_code == 500
        assert res.json() == {
            "error": "server error",
            "path": "/",
            "detail": "something's gone wrong",
            "status_code": 500,
        }

        res = client.get("/greet")
        assert res.status_code == 400
        assert res.json() == {
            "error": "validation error",
            "path": "/greet",
        }
