from unittest.mock import Mock, patch

from starlite.logging import LoggingConfig


@patch("logging.config.dictConfig")
def test_logging_debug(dictConfigMock: Mock):
    config = LoggingConfig()
    config.configure()
    assert dictConfigMock.call_args.args[0]["loggers"]["starlite"]["level"] == "INFO"
    dictConfigMock.reset_mock()
    config.configure(debug=True)
    assert dictConfigMock.call_args.args[0]["loggers"]["starlite"]["level"] == "DEBUG"
