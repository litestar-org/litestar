import logging
from typing import TYPE_CHECKING, Any, Dict
from unittest.mock import Mock, patch

import picologging
import pytest

from starlite import Starlite
from starlite.config.logging import default_handlers, default_picologging_handlers
from starlite.logging import LoggingConfig
from starlite.logging.picologging import QueueListenerHandler
from starlite.testing import TestClient, create_test_client

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


@pytest.mark.parametrize(
    "dict_config_class, handlers, expected_called",
    [
        ["logging.config.dictConfig", default_handlers, True],
        ["logging.config.dictConfig", default_picologging_handlers, False],
        ["picologging.config.dictConfig", default_handlers, False],
        ["picologging.config.dictConfig", default_picologging_handlers, True],
    ],
)
def test_correct_dict_config_called(
    dict_config_class: str, handlers: Dict[str, Dict[str, Any]], expected_called: bool
) -> None:
    with patch(dict_config_class) as dict_config_mock:
        log_config = LoggingConfig(handlers=handlers)
        log_config.configure()
        if expected_called:
            assert dict_config_mock.called
        else:
            assert not dict_config_mock.called


@pytest.mark.parametrize("picologging_exists", [True, False])
def test_correct_default_handlers_set(picologging_exists: bool) -> None:
    with patch("starlite.config.logging.find_spec") as find_spec_mock:
        find_spec_mock.return_value = picologging_exists
        log_config = LoggingConfig()

        if picologging_exists:
            assert log_config.handlers == default_picologging_handlers
        else:
            assert log_config.handlers == default_handlers


@patch("picologging.config.dictConfig")
def test_picologging_dictconfig_debug(dict_config_mock: Mock) -> None:
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


@patch("picologging.config.dictConfig")
def test_picologging_dictconfig_startup(dict_config_mock: Mock) -> None:
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


@patch("picologging.config.dictConfig")
def test_picologging_dictconfig_when_disabled(dict_config_mock: Mock) -> None:
    test_logger = LoggingConfig(loggers={"app": {"level": "INFO", "handlers": ["console"]}}, handlers=default_handlers)
    with create_test_client([], on_startup=[test_logger.configure]):
        assert not dict_config_mock.called


def test_queue_logger(caplog: "LogCaptureFixture") -> None:
    logger = logging.getLogger()

    with caplog.at_level(logging.INFO):
        logger.info("Testing now!")
        assert "Testing now!" in caplog.text


def test_logger_startup() -> None:
    with TestClient(
        app=Starlite(
            route_handlers=[],
            on_startup=[LoggingConfig(handlers=default_picologging_handlers).configure],
        )
    ) as client:
        client.options("/")
        test_picologging_handlers = picologging.getLogger().handlers
        assert isinstance(test_picologging_handlers[0], QueueListenerHandler)
