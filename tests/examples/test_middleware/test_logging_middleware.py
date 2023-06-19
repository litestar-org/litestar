import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import LogCaptureFixture

    from litestar.types.callable_types import GetLogger

from docs.examples.middleware.logging_middleware import app

from litestar.testing import TestClient


@pytest.mark.usefixtures("reset_httpx_logging")
def test_logging_middleware_regular_logger(get_logger: "GetLogger", caplog: "LogCaptureFixture") -> None:
    with TestClient(app=app) as client, caplog.at_level(logging.INFO):
        client.app.get_logger = get_logger
        response = client.get("/", headers={"request-header": "1"})
        assert response.status_code == 200
        assert len(caplog.messages) == 2
