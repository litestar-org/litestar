import logging
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

from starlite import Starlite
from starlite.config import LoggingConfig
from starlite.config.logging import default_handlers
from starlite.testing import TestClient, create_test_client

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


@patch("logging.config.dictConfig")
def test_logging_debug(dict_config_mock: Mock) -> None:
    config = LoggingConfig(handlers=default_handlers)
    config.configure()
    assert dict_config_mock.mock_calls[0][1][0]["loggers"]["starlite"]["level"] == "INFO"
    dict_config_mock.reset_mock()


@patch("logging.config.dictConfig")
def test_logging_startup(dict_config_mock: Mock) -> None:
    logger = LoggingConfig(handlers=default_handlers, loggers={"app": {"level": "INFO", "handlers": ["console"]}})
    with create_test_client([], on_startup=[logger.configure]):
        assert dict_config_mock.called


config = LoggingConfig()
config.configure()
logger = logging.getLogger()


def test_queue_logger(caplog: "LogCaptureFixture") -> None:
    """Test to check logging output contains the logged message."""
    with caplog.at_level(logging.INFO):
        logger.info("Testing now!")
        assert "Testing now!" in caplog.text


def test_logger_startup(caplog: "LogCaptureFixture") -> None:
    with TestClient(
        app=Starlite(route_handlers=[], on_startup=[LoggingConfig(handlers=default_handlers).configure])
    ) as client, caplog.at_level(logging.INFO):
        client.options("/")
        logger = logging.getLogger()
        handlers = logger.handlers
        assert isinstance(handlers[0].handlers[0], logging.StreamHandler)  # type: ignore
