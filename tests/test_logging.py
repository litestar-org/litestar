import logging
from unittest.mock import Mock, patch

from _pytest.logging import LogCaptureFixture

from starlite import Starlite
from starlite.logging import LoggingConfig
from starlite.testing import TestClient, create_test_client


@patch("logging.config.dictConfig")
def test_logging_debug(dict_config_mock: Mock) -> None:
    config = LoggingConfig()
    config.configure()
    assert dict_config_mock.mock_calls[0][1][0]["loggers"]["starlite"]["level"] == "INFO"
    dict_config_mock.reset_mock()


@patch("logging.config.dictConfig")
def test_logging_startup(dict_config_mock: Mock) -> None:
    logger = LoggingConfig(loggers={"app": {"level": "INFO", "handlers": ["console"]}})
    with create_test_client([], on_startup=[logger.configure]):
        assert dict_config_mock.called


config = LoggingConfig()
config.configure()
logger = logging.getLogger()


def test_queue_logger(caplog: LogCaptureFixture) -> None:
    """
    Test to check logging output contains the logged message
    """
    with caplog.at_level(logging.INFO):
        logger.info("Testing now!")
        assert "Testing now!" in caplog.text


def test_logger_statup(caplog: LogCaptureFixture) -> None:
    with TestClient(app=Starlite(route_handlers=[], on_startup=[LoggingConfig().configure])) as client, caplog.at_level(
        logging.INFO
    ):
        client.options("/")
        logger = logging.getLogger()
        handlers = logger.handlers
        assert isinstance(handlers[0].handlers[0], logging.StreamHandler)  # type: ignore
