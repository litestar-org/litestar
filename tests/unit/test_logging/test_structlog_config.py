import datetime
import sys
from typing import Callable, Set, Type, Union
from unittest.mock import MagicMock, patch

import pytest
import structlog
from pytest import CaptureFixture
from structlog import BytesLoggerFactory, get_logger
from structlog.processors import JSONRenderer
from structlog.types import BindableLogger, WrappedLogger

from litestar import get
from litestar.exceptions import HTTPException, NotFoundException
from litestar.logging.config import LoggingConfig, StructlogEventFilter, StructLoggingConfig, default_json_serializer
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin
from litestar.serialization import decode_json
from litestar.testing import create_test_client

# structlog.testing.capture_logs changes the processors
# Because we want to test processors, use capsys instead


def test_event_filter() -> None:
    """Functionality test for the event filter processor."""
    event_filter = StructlogEventFilter(["a_key"])
    log_event = {"a_key": "a_val", "b_key": "b_val"}
    log_event = event_filter(..., "", log_event)  # type:ignore[assignment]
    assert log_event == {"b_key": "b_val"}


def test_set_level_custom_logger_factory() -> None:
    """Functionality test for the event filter processor."""

    def custom_logger_factory() -> Callable[..., WrappedLogger]:
        """Set the default logger factory for structlog.

        Returns:
            An optional logger factory.
        """
        return BytesLoggerFactory()

    log_config = StructLoggingConfig(logger_factory=custom_logger_factory, wrapper_class=structlog.stdlib.BoundLogger)
    logger = get_logger()
    assert logger.bind().__class__.__name__ != "BoundLoggerFilteringAtDebug"
    log_config.set_level(logger, 10)
    logger.info("a message")
    assert logger.bind().__class__.__name__ == "BoundLoggerFilteringAtDebug"


def test_structlog_plugin(capsys: CaptureFixture) -> None:
    with create_test_client([], plugins=[StructlogPlugin()]) as client:
        assert client.app.logger
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

        log_messages = [decode_json(value=x) for x in capsys.readouterr().out.splitlines()]
        assert len(log_messages) == 1

        # Format should be: {event: message, key: value, level: info, timestamp: isoformat}
        log_messages[0].pop("timestamp")  # Assume structlog formats timestamp correctly
        assert log_messages[0] == {"event": "message", "key": "value", "level": "info"}


def test_structlog_plugin_config(capsys: CaptureFixture) -> None:
    config = StructlogConfig()
    with create_test_client([], plugins=[StructlogPlugin(config=config)]) as client:
        assert client.app.logger
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

        log_messages = [decode_json(value=x) for x in capsys.readouterr().out.splitlines()]
        assert len(log_messages) == 1
        assert client.app.plugins.get(StructlogPlugin)._config == config


def test_structlog_plugin_config_custom_standard_logger() -> None:
    standard_logging_config = LoggingConfig()
    structlog_logging_config = StructLoggingConfig(standard_lib_logging_config=standard_logging_config)
    config = StructlogConfig(structlog_logging_config=structlog_logging_config)
    with create_test_client([], plugins=[StructlogPlugin(config=config)]) as client:
        assert client.app.plugins.get(StructlogPlugin)._config == config
        assert (
            client.app.plugins.get(StructlogPlugin)._config.structlog_logging_config.standard_lib_logging_config
            == standard_logging_config
        )


def test_structlog_plugin_config_custom() -> None:
    structlog_logging_config = StructLoggingConfig(standard_lib_logging_config=None)
    config = StructlogConfig(structlog_logging_config=structlog_logging_config)
    with create_test_client([], plugins=[StructlogPlugin(config=config)]) as client:
        assert client.app.plugins.get(StructlogPlugin)._config == config
        assert client.app.plugins.get(StructlogPlugin)._config.structlog_logging_config == structlog_logging_config
        assert (
            client.app.plugins.get(StructlogPlugin)._config.structlog_logging_config.standard_lib_logging_config
            is not None
        )


def test_structlog_plugin_config_with_existing_logging_config(capsys: CaptureFixture) -> None:
    existing_log_config = StructLoggingConfig()
    standard_logging_config = LoggingConfig()
    structlog_logging_config = StructLoggingConfig(standard_lib_logging_config=standard_logging_config)
    config = StructlogConfig(structlog_logging_config=structlog_logging_config)
    with create_test_client([], logging_config=existing_log_config, plugins=[StructlogPlugin(config=config)]) as client:
        assert client.app.plugins.get(StructlogPlugin)._config == config
        assert "Found pre-configured" in capsys.readouterr().out


def test_structlog_config_no_tty_default(capsys: CaptureFixture) -> None:
    with create_test_client([], logging_config=StructLoggingConfig()) as client:
        assert client.app.logger
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

        log_messages = [decode_json(value=x) for x in capsys.readouterr().out.splitlines()]
        assert len(log_messages) == 1

        # Format should be: {event: message, key: value, level: info, timestamp: isoformat}
        log_messages[0].pop("timestamp")  # Assume structlog formats timestamp correctly
        assert log_messages[0] == {"event": "message", "key": "value", "level": "info"}


def test_structlog_config_tty_default(capsys: CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    from sys import stderr

    monkeypatch.setattr(stderr, "isatty", lambda: True)

    with create_test_client([], logging_config=StructLoggingConfig()) as client:
        assert client.app.logger
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

        log_messages = capsys.readouterr().out.splitlines()
        assert len(log_messages) == 1

        if sys.platform.startswith("win"):
            assert log_messages[0].startswith(str(datetime.datetime.now().year))
        else:
            assert log_messages[0].startswith("\x1b[")


def test_structlog_config_specify_processors(capsys: CaptureFixture) -> None:
    logging_config = StructLoggingConfig(processors=[JSONRenderer(serializer=default_json_serializer)])

    with create_test_client([], logging_config=logging_config) as client:
        assert client.app.logger
        assert isinstance(client.app.logger.bind(), BindableLogger)

        client.app.logger.info("message1", key="value1")
        # Log twice to make sure issue #882 doesn't appear again
        client.app.logger.info("message2", key="value2")

        log_messages = [decode_json(value=x) for x in capsys.readouterr().out.splitlines()]

        assert log_messages == [
            {"key": "value1", "event": "message1"},
            {"key": "value2", "event": "message2"},
        ]


@pytest.mark.parametrize(
    "isatty, pretty_print_tty, expected_as_json",
    [
        (True, True, False),
        (True, False, True),
        (False, True, True),
        (False, False, True),
    ],
)
def test_structlog_config_as_json(isatty: bool, pretty_print_tty: bool, expected_as_json: bool) -> None:
    with patch("litestar.logging.config.sys.stderr.isatty") as isatty_mock:
        isatty_mock.return_value = isatty
        logging_config = StructLoggingConfig(pretty_print_tty=pretty_print_tty)
        assert logging_config.as_json() is expected_as_json


@pytest.mark.parametrize(
    "disable_stack_trace, exception_to_raise, handler_called",
    [
        # will log the stack trace
        [set(), HTTPException, True],
        [set(), ValueError, True],
        [{400}, HTTPException, True],
        [{NameError}, ValueError, True],
        [{400, NameError}, ValueError, True],
        # will not log the stack trace
        [{NotFoundException}, HTTPException, False],
        [{404}, HTTPException, False],
        [{ValueError}, ValueError, False],
        [{400, ValueError}, ValueError, False],
        [{404, NameError}, HTTPException, False],
    ],
)
def test_structlog_disable_stack_trace(
    disable_stack_trace: Set[Union[int, Type[Exception]]],
    exception_to_raise: Type[Exception],
    handler_called: bool,
) -> None:
    mock_handler = MagicMock()

    logging_config = StructLoggingConfig(
        disable_stack_trace=disable_stack_trace, exception_logging_handler=mock_handler
    )

    @get("/error")
    async def error_route() -> None:
        raise exception_to_raise

    with create_test_client([error_route], logging_config=logging_config, debug=True) as client:
        if exception_to_raise is HTTPException:
            _ = client.get("/404-error")
        else:
            _ = client.get("/error")

        if handler_called:
            assert mock_handler.called, "Structlog exception handler should have been called"
        else:
            assert not mock_handler.called, "Structlog exception handler should not have been called"
