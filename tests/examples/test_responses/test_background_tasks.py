import logging
from typing import TYPE_CHECKING

import pytest
from docs.examples.responses.background_tasks_1 import app as app_1
from docs.examples.responses.background_tasks_2 import app as app_2
from docs.examples.responses.background_tasks_3 import app as app_3
from docs.examples.responses.background_tasks_3 import greeted as greeted_3

from litestar.testing import TestClient

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


pytestmark = pytest.mark.usefixtures("reset_httpx_logging")


def test_background_tasks_1(caplog: "LogCaptureFixture") -> None:
    with caplog.at_level(logging.INFO), TestClient(app=app_1) as client:
        name = "Jane"
        res = client.get("/", params={"name": name})
        assert res.status_code == 200
        assert res.json()["hello"] == name
        assert len(caplog.messages) == 1
        assert name in caplog.messages[0]


def test_background_tasks_2(caplog: "LogCaptureFixture") -> None:
    with caplog.at_level(logging.INFO), TestClient(app=app_2) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert "hello" in res.json()
        assert len(caplog.messages) == 1
        assert "greeter" in caplog.messages[0]


def test_background_tasks_3(caplog: "LogCaptureFixture") -> None:
    with caplog.at_level(logging.INFO), TestClient(app=app_3) as client:
        name = "Jane"
        res = client.get("/", params={"name": name})
        assert res.status_code == 200
        assert res.json()["hello"] == name
        assert len(caplog.messages) == 1
        assert name in caplog.messages[0]
        assert name in greeted_3
