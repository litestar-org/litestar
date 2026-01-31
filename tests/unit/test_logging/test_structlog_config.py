# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

import datetime
from typing import Union
from unittest.mock import MagicMock, patch, ANY

import pytest
import structlog
from structlog.processors import JSONRenderer
from structlog.types import BindableLogger

from litestar import get
from litestar.exceptions import HTTPException, NotFoundException
from litestar.logging.structlog import StructLoggingConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin
from litestar.serialization import decode_json
from litestar.testing import create_test_client


@pytest.fixture(autouse=True)
def reset_structlog() -> None:
    structlog.reset_defaults()


def test_structlog_plugin(caplog: pytest.LogCaptureFixture) -> None:
    with create_test_client([], plugins=[StructlogPlugin()]) as client:
        assert isinstance(client.app.logger, structlog._config.BoundLoggerLazyProxy)
        assert isinstance(client.app.logger.bind(), BindableLogger)

        client.app.logger.info("message", key="value")

    log_messages = [decode_json(value=x) for x in caplog.messages]
    assert len(log_messages) == 1

    # Format should be: {event: message, key: value, level: info, timestamp: isoformat}
    log_messages[0].pop("timestamp")  # Assume structlog formats timestamp correctly
    assert log_messages[0] == {"event": "message", "key": "value", "level": "info"}


def test_structlog_plugin_config(caplog: pytest.LogCaptureFixture) -> None:
    config = StructlogConfig()
    with create_test_client([], plugins=[StructlogPlugin(config=config)]) as client:
        assert isinstance(client.app.logger, structlog._config.BoundLoggerLazyProxy)
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

    log_messages = [decode_json(value=x) for x in caplog.messages]
    assert len(log_messages) == 1
    assert client.app.plugins.get(StructlogPlugin)._config == config


def test_structlog_plugin_config_with_existing_logging_config(caplog: pytest.LogCaptureFixture) -> None:
    existing_log_config = StructLoggingConfig()
    structlog_logging_config = StructLoggingConfig()
    config = StructlogConfig(structlog_logging_config=structlog_logging_config)
    with create_test_client([], logging_config=existing_log_config, plugins=[StructlogPlugin(config=config)]) as client:
        assert client.app.plugins.get(StructlogPlugin)._config == config
        client.app.logger.info("message", key="value")

    assert decode_json(caplog.messages[0]) == {"event": "message", "key": "value", "level": "info", "timestamp": ANY}


def test_structlog_config_no_tty_default(caplog: pytest.LogCaptureFixture) -> None:
    with create_test_client([], logging_config=StructLoggingConfig()) as client:
        assert isinstance(client.app.logger, structlog._config.BoundLoggerLazyProxy)
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

    log_messages = [decode_json(value=x) for x in caplog.messages]
    assert len(log_messages) == 1

    # Format should be: {event: message, key: value, level: info, timestamp: isoformat}
    log_messages[0].pop("timestamp")  # Assume structlog formats timestamp correctly
    assert log_messages[0] == {"event": "message", "key": "value", "level": "info"}


def test_structlog_config_tty_default(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, mocker
) -> None:
    # from sys import stderr

    # monkeypatch.setattr(stderr, "isatty", lambda: True)
    mocker.patch("litestar.logging.structlog.sys.stderr.isatty", return_value=True)

    with create_test_client([], logging_config=StructLoggingConfig()) as client:
        assert isinstance(client.app.logger, structlog._config.BoundLoggerLazyProxy)
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

    log_messages = caplog.messages
    assert len(log_messages) == 1

    assert log_messages[0].startswith(str(datetime.datetime.now().year))


def test_structlog_config_specify_processors(caplog: pytest.LogCaptureFixture) -> None:
    logging_config = StructLoggingConfig(processors=[JSONRenderer()])

    with create_test_client([], logging_config=logging_config) as client:
        assert isinstance(client.app.logger, structlog._config.BoundLoggerLazyProxy)
        assert isinstance(client.app.logger.bind(), BindableLogger)

        client.app.logger.info("message1", key="value1")
        # Log twice to make sure issue #882 doesn't appear again
        client.app.logger.info("message2", key="value2")

    log_messages = [decode_json(value=x) for x in caplog.messages]

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
    with patch("litestar.logging.structlog.sys.stderr.isatty") as isatty_mock:
        isatty_mock.return_value = isatty
        logging_config = StructLoggingConfig(pretty_print_tty=pretty_print_tty)
        assert logging_config.should_log_as_json is expected_as_json


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
    disable_stack_trace: set[Union[int, type[Exception]]],
    exception_to_raise: type[Exception],
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
