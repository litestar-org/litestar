# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

import datetime
from unittest.mock import patch

import pytest
import structlog
from pytest_mock import MockerFixture
from structlog.processors import JSONRenderer
from structlog.types import BindableLogger

from litestar.logging.structlog import StructLoggingConfig
from litestar.middleware.logging import LoggingMiddleware
from litestar.serialization import decode_json
from litestar.testing import create_test_client


@pytest.fixture(autouse=True)
def reset_structlog() -> None:
    structlog.reset_defaults()


def test_structlog_plugin(caplog: pytest.LogCaptureFixture) -> None:
    with create_test_client(
        [],
        logging_config=StructLoggingConfig(),
        middleware=[LoggingMiddleware()],
    ) as client:
        assert isinstance(client.app.logger, structlog._config.BoundLoggerLazyProxy)
        assert isinstance(client.app.logger.bind(), BindableLogger)

        client.app.logger.info("message", key="value")

    log_messages = [decode_json(value=x) for x in caplog.messages]
    assert len(log_messages) == 1

    # Format should be: {event: message, key: value, level: info, timestamp: isoformat}
    log_messages[0].pop("timestamp")  # Assume structlog formats timestamp correctly
    assert log_messages[0] == {"event": "message", "key": "value", "level": "info"}


def test_structlog_plugin_config(caplog: pytest.LogCaptureFixture) -> None:
    with create_test_client(
        [],
        logging_config=StructLoggingConfig(),
        middleware=[LoggingMiddleware()],
    ) as client:
        assert isinstance(client.app.logger, structlog._config.BoundLoggerLazyProxy)
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

    log_messages = [decode_json(value=x) for x in caplog.messages]
    assert len(log_messages) == 1


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
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
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
