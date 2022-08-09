import logging
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import picologging

from starlite import Starlite
from starlite.logging import LoggingConfig
from starlite.testing import TestClient, create_test_client

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


@patch("logging.config.dictConfig")
def test_logging_debug(dict_config_mock: Mock) -> None:
    log_config = LoggingConfig(
        handlers={
            "console": {
                "class": "picologging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
            },
            "queue_listener": {
                "class": "starlite.logging.picologging.QueueListenerHandler",
                "handlers": ["cfg://handlers.console"],
            },
        }
    )
    log_config.configure()
    assert dict_config_mock.mock_calls[0][1][0]["loggers"]["starlite"]["level"] == "INFO"
    dict_config_mock.reset_mock()


@patch("logging.config.dictConfig")
def test_logging_startup(dict_config_mock: Mock) -> None:
    test_logger = LoggingConfig(
        handlers={
            "console": {
                "class": "picologging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
            },
            "queue_listener": {
                "class": "starlite.logging.picologging.QueueListenerHandler",
                "handlers": ["cfg://handlers.console"],
            },
        },
        loggers={"app": {"level": "INFO", "handlers": ["console"]}},
    )
    with create_test_client([], on_startup=[test_logger.configure]):
        assert dict_config_mock.called


logger = logging.getLogger()
config = LoggingConfig(
    handlers={
        "console": {
            "class": "picologging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
        },
        "queue_listener": {
            "class": "starlite.logging.picologging.QueueListenerHandler",
            "handlers": ["cfg://handlers.console"],
        },
    }
)
config.configure()


def test_queue_logger(caplog: "LogCaptureFixture") -> None:
    """
    Test to check logging output contains the logged message
    """

    with caplog.at_level(logging.INFO):
        logger.info("Testing now!")
        assert "Testing now!" in caplog.text


def test_logger_startup(caplog: "LogCaptureFixture") -> None:
    with TestClient(
        app=Starlite(
            route_handlers=[],
            on_startup=[
                LoggingConfig(
                    handlers={
                        "console": {
                            "class": "picologging.StreamHandler",
                            "level": "DEBUG",
                            "formatter": "standard",
                        },
                        "queue_listener": {
                            "class": "starlite.logging.picologging.QueueListenerHandler",
                            "handlers": ["cfg://handlers.console"],
                        },
                    }
                ).configure
            ],
        )
    ) as client, caplog.at_level(logging.INFO):
        client.options("/")
        test_logger = logging.getLogger()
        handlers = test_logger.handlers
        assert isinstance(handlers[0].handlers[0], picologging.StreamHandler)  # type: ignore
