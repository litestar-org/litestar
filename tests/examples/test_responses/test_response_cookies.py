from unittest.mock import patch

from docs.examples.responses.response_cookies_1 import app
from docs.examples.responses.response_cookies_2 import app as app_2
from docs.examples.responses.response_cookies_3 import app as app_3
from docs.examples.responses.response_cookies_4 import app as app_4
from docs.examples.responses.response_cookies_5 import app as app_5

from litestar.testing import TestClient


def test_response_cookies() -> None:
    with TestClient(app=app) as client:
        res = client.get("/router-path/controller-path")
        assert res.status_code == 200
        assert res.cookies["local-cookie"] == '"local value"'
        assert res.cookies["controller-cookie"] == '"controller value"'
        assert res.cookies["router-cookie"] == '"router value"'
        assert res.cookies["app-cookie"] == '"app value"'


def test_response_cookies_2() -> None:
    with TestClient(app=app_2) as client:
        res = client.get("/controller-path")
        assert res.status_code == 200
        assert res.cookies["my-cookie"] == "456"


def test_response_cookies_3() -> None:
    with TestClient(app=app_3) as client, patch("docs.examples.responses.response_cookies_3.randint") as mock_randint:
        mock_randint.return_value = "42"

        res = client.get("/resources")

        assert res.status_code == 200
        assert res.cookies["Random-Cookie"] == "42"


def test_response_cookies_4() -> None:
    with TestClient(app=app_4) as client, patch("docs.examples.responses.response_cookies_4.randint") as mock_randint:
        mock_randint.return_value = "42"

        res = client.get("/router-path/resources")

        assert res.status_code == 200
        assert res.cookies["Random-Cookie"] == "42"


def test_response_cookies_5() -> None:
    with TestClient(app=app_5) as client, patch("docs.examples.responses.response_cookies_5.randint") as mock_randint:
        mock_randint.return_value = "42"

        res = client.get("/router-path/resources")

        assert res.status_code == 200
        assert res.cookies["Random-Cookie"] == "42"
