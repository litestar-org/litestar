from unittest.mock import Mock, patch

from starlite.logging import LoggingConfig


@patch("logging.config.dictConfig")
def test_logging_debug(dict_config_mock: Mock):
    config = LoggingConfig()
    config.configure()
    assert dict_config_mock.mock_calls[0][1][0]["loggers"]["starlite"]["level"] == "INFO"
    dict_config_mock.reset_mock()
