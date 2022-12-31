import logging

import pytest
from pytest import LogCaptureFixture

from examples.middleware.logging_middleware import app
from starlite import LoggingConfig
from starlite import TestClient
from starlite.config.logging import default_handlers
from starlite.types.callable_types import GetLogger


@pytest.fixture
def get_logger() -> "GetLogger":
    # due to the limitations of caplog we have to place this call here.
    # we also have to allow propagation.
    return LoggingConfig(
        handlers=default_handlers,
        loggers={
            "starlite": {"level": "INFO", "handlers": ["queue_listener"], "propagate": True},
        },
    ).configure()


def test_logging_middleware_regular_logger(get_logger: "GetLogger", caplog: "LogCaptureFixture") -> None:
    with TestClient(app=app) as client, caplog.at_level(logging.INFO):
        client.app.get_logger = get_logger
        response = client.get("/", headers={"request-header": "1"})
        assert response.status_code == 200
        assert len(caplog.messages) == 2
