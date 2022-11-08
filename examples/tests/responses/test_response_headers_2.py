from unittest.mock import patch

from examples.responses.response_headers_2 import app
from starlite import TestClient


def test_response_headers() -> None:
    with TestClient(app=app) as client, patch("examples.responses.response_headers_2.randint") as mock_randint:
        mock_randint.return_value = "42"
        res = client.get("/resources")
        assert res.status_code == 200
        assert res.headers["Random-Header"] == "42"
