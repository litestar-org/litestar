from unittest.mock import patch

from examples.responses.response_cookies_5 import app
from starlite import TestClient


def test_response_cookies() -> None:
    with TestClient(app=app) as client, patch("examples.responses.response_cookies_5.randint") as mock_randint:
        mock_randint.return_value = "42"

        res = client.get("/router-path/resources")

        assert res.status_code == 200
        assert res.cookies["Random-Cookie"] == "42"
