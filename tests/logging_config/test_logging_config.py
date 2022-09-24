from typing import TYPE_CHECKING, Any, Dict
from unittest.mock import Mock, patch

import pytest
from starlette.status import HTTP_200_OK

from starlite import Request, get
from starlite.config import LoggingConfig
from starlite.config.logging import default_handlers, default_picologging_handlers
from starlite.logging.picologging import (
    QueueListenerHandler as PicologgingQueueListenerHandler,
)
from starlite.logging.standard import (
    QueueListenerHandler as StandardQueueListenerHandler,
)
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture

    from starlite.types import Logger


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


@pytest.mark.parametrize(
    "dict_config_class, handlers",
    [
        ["logging.config.dictConfig", default_handlers],
        ["picologging.config.dictConfig", default_picologging_handlers],
    ],
)
def test_dictconfig_startup(dict_config_class: str, handlers: Any) -> None:
    with patch(dict_config_class) as dict_config_mock:
        test_logger = LoggingConfig(handlers=handlers)
        with create_test_client([], on_startup=[test_logger.configure]):
            assert dict_config_mock.called


@pytest.mark.parametrize("logger", [LoggingConfig(handlers=default_handlers).configure()("starlite")])
def test_standard_queue_listener_logger(logger: "Logger", caplog: "LogCaptureFixture") -> None:
    with caplog.at_level("INFO"):
        logger.info("Testing now!")
        assert "Testing now!" in caplog.text


@pytest.mark.xfail(reason="see: https://github.com/microsoft/picologging/issues/90")
@pytest.mark.parametrize("logger", [LoggingConfig(handlers=default_picologging_handlers).configure()("starlite")])
def test_picologging_queue_listener_logger(logger: "Logger", caplog: "LogCaptureFixture") -> None:
    with caplog.at_level("INFO"):
        logger.info("Testing now!")
        assert "Testing now!" in caplog.text


@patch("picologging.config.dictConfig")
def test_picologging_dictconfig_when_disabled(dict_config_mock: Mock) -> None:
    test_logger = LoggingConfig(loggers={"app": {"level": "INFO", "handlers": ["console"]}}, handlers=default_handlers)
    with create_test_client([], on_startup=[test_logger.configure]):
        assert not dict_config_mock.called


def test_get_default_logger() -> None:
    with create_test_client(route_handlers=[], logging_config=LoggingConfig(handlers=default_handlers)) as client:
        assert isinstance(client.app.logger.handlers[0], StandardQueueListenerHandler)  # type: ignore
        new_logger = client.app.get_logger()
        assert isinstance(new_logger.handlers[0], StandardQueueListenerHandler)  # type: ignore


def test_get_picologging_logger() -> None:
    with create_test_client(
        route_handlers=[], logging_config=LoggingConfig(handlers=default_picologging_handlers)
    ) as client:
        assert isinstance(client.app.logger.handlers[0], PicologgingQueueListenerHandler)  # type: ignore
        new_logger = client.app.get_logger()
        assert isinstance(new_logger.handlers[0], PicologgingQueueListenerHandler)  # type: ignore


@pytest.mark.parametrize(
    "handlers, listener",
    [
        [default_handlers, StandardQueueListenerHandler],
        [default_picologging_handlers, PicologgingQueueListenerHandler],
    ],
)
def test_connection_logger(handlers: Any, listener: Any) -> None:
    @get("/")
    def handler(request: Request) -> Dict[str, bool]:
        return {"isinstance": isinstance(request.logger.handlers[0], listener)}  # type: ignore

    with create_test_client(route_handlers=[handler], logging_config=LoggingConfig(handlers=handlers)) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.json()["isinstance"]
