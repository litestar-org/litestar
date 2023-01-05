from unittest.mock import patch

from examples.responses.background_tasks_2 import app as app_2
from starlite import TestClient


def test_background_tasks_2() -> None:
    with TestClient(app=app_2) as client, patch("examples.responses.background_tasks_2.logger.info") as mock_info:
        res = client.get("/")
        assert res.status_code == 200
        mock_info.assert_called_once()
