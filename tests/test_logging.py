from unittest.mock import Mock, patch

from starlite import create_test_client
from starlite.logging import LoggingConfig


@patch("logging.config.dictConfig")
def test_logging_debug(dict_config_mock: Mock):
    config = LoggingConfig()
    config.configure()
    assert dict_config_mock.mock_calls[0][1][0]["loggers"]["starlite"]["level"] == "INFO"
    dict_config_mock.reset_mock()


@patch("logging.config.dictConfig")
def test_logging_startup(dict_config_mock: Mock):
    logger = LoggingConfig(loggers={"app": {"level": "INFO", "handlers": ["console"]}})
    with create_test_client([], on_startup=[logger.configure]):
        assert dict_config_mock.called
