from unittest.mock import patch

from docs.examples.responses.response_headers_1 import app
from docs.examples.responses.response_headers_2 import app as app_2
from docs.examples.responses.response_headers_3 import app as app_3
from docs.examples.responses.response_headers_4 import app as app_4

from litestar.testing import TestClient


def test_response_headers() -> None:
    with TestClient(app=app) as client:
        res = client.get("/router-path/controller-path/handler-path")
        assert res.status_code == 200
        assert res.headers["my-local-header"] == "local header"
        assert res.headers["controller-level-header"] == "controller header"
        assert res.headers["router-level-header"] == "router header"
        assert res.headers["app-level-header"] == "app header"


def test_response_headers_2() -> None:
    with TestClient(app=app_2) as client, patch("docs.examples.responses.response_headers_2.randint") as mock_randint:
        mock_randint.return_value = "42"
        res = client.get("/resources")
        assert res.status_code == 200
        assert res.headers["Random-Header"] == "42"


def test_response_headers_3() -> None:
    with TestClient(app=app_3) as client, patch("docs.examples.responses.response_headers_3.randint") as mock_randint:
        mock_randint.return_value = "42"
        res = client.get("/router-path/resources")
        assert res.status_code == 200
        assert res.headers["Random-Header"] == "42"
        assert res.json() == {"id": 1, "name": "my resource"}


def test_response_headers_4() -> None:
    with TestClient(app=app_4) as client, patch("docs.examples.responses.response_headers_4.randint") as mock_randint:
        mock_randint.return_value = "42"
        res = client.get("/router-path/resources")
        assert res.status_code == 200
        assert res.headers["Random-Header"] == "42"
        assert res.json() == {"id": 1, "name": "my resource"}
