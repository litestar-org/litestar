from unittest.mock import patch

from examples.responses.background_tasks_1 import app as app_1
from examples.responses.background_tasks_2 import app as app_2
from examples.responses.background_tasks_3 import app as app_3
from examples.responses.background_tasks_3 import greeted as greeted_3
from starlite import TestClient


def test_background_tasks_1() -> None:
    with TestClient(app=app_1) as client, patch("examples.responses.background_tasks_1.logger.info") as mock_info:
        name = "Jane"
        res = client.get("/", params={"name": name})
        assert res.status_code == 200
        assert res.json()["hello"] == name
        mock_info.assert_called_once()
        mock_call_args: tuple[str] = mock_info.call_args[0]
        assert any([name in arg for arg in mock_call_args])


def test_background_tasks_2() -> None:
    with TestClient(app=app_2) as client, patch("examples.responses.background_tasks_2.logger.info") as mock_info:
        res = client.get("/")
        assert res.status_code == 200
        assert "hello" in res.json()
        mock_info.assert_called_once()
        mock_call_args: tuple[str] = mock_info.call_args[0]
        assert any(["greeter" in arg for arg in mock_call_args])


def test_background_tasks_3() -> None:
    with TestClient(app=app_3) as client, patch("examples.responses.background_tasks_3.logger.info") as mock_info:
        name = "Jane"
        res = client.get("/", params={"name": name})
        assert res.status_code == 200
        assert res.json()["hello"] == name
        mock_info.assert_called_once()
        mock_call_args: tuple[str] = mock_info.call_args[0]
        assert any([name in arg for arg in mock_call_args])
        assert name in greeted_3
