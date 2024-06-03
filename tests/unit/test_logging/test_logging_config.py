import logging
import sys
import time
from importlib.util import find_spec
from logging.handlers import QueueHandler
from queue import Queue
from types import ModuleType
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional
from unittest.mock import patch

import picologging
import pytest
from _pytest.logging import LogCaptureHandler, _LiveLoggingNullHandler

from litestar import Request, get
from litestar.exceptions import ImproperlyConfiguredException
from litestar.logging.config import (
    LoggingConfig,
    _get_default_handlers,
    default_handlers,
    default_picologging_handlers,
)
from litestar.logging.picologging import QueueListenerHandler as PicologgingQueueListenerHandler
from litestar.logging.standard import LoggingQueueListener
from litestar.logging.standard import QueueListenerHandler as StandardQueueListenerHandler
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client
from tests.helpers import cleanup_logging_impl

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture


@pytest.fixture(autouse=True)
def cleanup_logging() -> Generator:
    with cleanup_logging_impl():
        yield


def test__get_default_handlers() -> None:
    assert find_spec("picologging")  # picologging should be installed in the test environment, simply checking that
    assert _get_default_handlers() == default_picologging_handlers

    with patch("litestar.logging.config.find_spec") as find_spec_mock:
        find_spec_mock.return_value = None
        assert _get_default_handlers() == default_handlers


@pytest.mark.parametrize(
    "dict_config_callable, default_handlers, expected_called",
    [
        ["logging.config.dictConfig", default_handlers, True],
        ["logging.config.dictConfig", default_picologging_handlers, False],
        ["picologging.config.dictConfig", default_handlers, False],
        ["picologging.config.dictConfig", default_picologging_handlers, True],
    ],
)
def test_correct_dict_config_called(
    dict_config_callable: str,
    default_handlers: Dict[str, Dict[str, Any]],
    expected_called: bool,
) -> None:
    with patch(dict_config_callable) as dict_config_mock:
        log_config = LoggingConfig(handlers=default_handlers)
        log_config.configure()
        if expected_called:
            assert dict_config_mock.called
        else:
            assert not dict_config_mock.called


@pytest.mark.parametrize(
    "picologging_exists, expected_default_handlers",
    [
        [True, default_picologging_handlers],
        [False, default_handlers],
    ],
)
def test_correct_default_handlers_set(picologging_exists: bool, expected_default_handlers: Any) -> None:
    with patch("litestar.logging.config.find_spec") as find_spec_mock:
        find_spec_mock.return_value = picologging_exists
        log_config = LoggingConfig()
        assert log_config.handlers == expected_default_handlers


@pytest.mark.parametrize(
    "dict_config_callable, dict_config_not_called, handlers",
    [
        ["logging.config.dictConfig", "picologging.config.dictConfig", default_handlers],
        ["picologging.config.dictConfig", "logging.config.dictConfig", default_picologging_handlers],
    ],
)
def test_dictconfig_on_startup(dict_config_callable: str, dict_config_not_called: str, handlers: Any) -> None:
    with patch(dict_config_callable) as dict_config_mock:
        with patch(dict_config_not_called) as dict_config_not_called_mock:
            test_logger = LoggingConfig(
                handlers=handlers,
                loggers={"app": {"level": "INFO", "handlers": ["console"]}},
            )

            with create_test_client([], on_startup=[test_logger.configure], logging_config=None):
                assert dict_config_mock.called
                assert dict_config_mock.call_count == 1
                assert dict_config_not_called_mock.call_count == 0


@pytest.mark.parametrize(
    "logging_module, expected_handler_class, expected_listener_class",
    [
        [
            logging,
            QueueHandler if sys.version_info >= (3, 12, 0) else StandardQueueListenerHandler,
            LoggingQueueListener,
        ],
        [
            picologging,
            PicologgingQueueListenerHandler,
            picologging.handlers.QueueListener,  # pyright: ignore[reportGeneralTypeIssues]
        ],
    ],
)
def test_default_queue_listener_handler(
    logging_module: ModuleType, expected_handler_class: Any, expected_listener_class: Any, capsys: "CaptureFixture[str]"
) -> None:
    def wait_log_queue(queue: Any, sleep_time: float = 0.1, max_retries: int = 5) -> None:
        retry = 0
        while queue.qsize() > 0 and retry < max_retries:
            retry += 1
            time.sleep(sleep_time)

    def assert_log(queue: Any, expected: str, count: Optional[int] = None) -> None:
        wait_log_queue(queue)
        log_output = capsys.readouterr().err.strip()
        if count is not None:
            assert len(log_output.split("\n")) == count
        assert log_output == expected

    with patch("litestar.logging.config.find_spec") as find_spec_mock:
        find_spec_mock.return_value = None if logging_module is logging else True

        get_logger = LoggingConfig(
            formatters={"standard": {"format": "%(levelname)s :: %(name)s :: %(message)s"}},
            loggers={
                "test_logger": {
                    "level": "INFO",
                    "handlers": ["queue_listener"],
                    "propagate": False,
                },
            },
        ).configure()

    logger = get_logger("test_logger")
    assert type(logger) is logging_module.Logger

    handler = logger.handlers[0]  # pyright: ignore[reportGeneralTypeIssues]
    assert type(handler) is expected_handler_class
    assert type(handler.queue) is Queue

    assert type(handler.listener) is expected_listener_class
    assert type(handler.listener.handlers[0]) is logging_module.StreamHandler

    logger.info("Testing now!")
    assert_log(handler.queue, expected="INFO :: test_logger :: Testing now!", count=1)

    var = "test_var"
    logger.info("%s", var)
    assert_log(handler.queue, expected="INFO :: test_logger :: test_var", count=1)


def test_get_logger_without_logging_config() -> None:
    with create_test_client(logging_config=None) as client:
        with pytest.raises(
            ImproperlyConfiguredException,
            match="cannot call '.get_logger' without passing 'logging_config' to the Litestar constructor first",
        ):
            client.app.get_logger()


@pytest.mark.parametrize(
    "logging_module, handlers, expected_handler_class",
    [
        [logging, default_handlers, QueueHandler if sys.version_info >= (3, 12, 0) else StandardQueueListenerHandler],
        [picologging, default_picologging_handlers, PicologgingQueueListenerHandler],
    ],
)
def test_default_loggers(logging_module: ModuleType, handlers: Any, expected_handler_class: Any) -> None:
    with create_test_client(logging_config=LoggingConfig(handlers=handlers)) as client:
        root_logger = client.app.get_logger()
        assert isinstance(root_logger, logging_module.Logger)
        assert root_logger.name == "root"
        assert type(root_logger.handlers[0]) is expected_handler_class

        litestar_logger = client.app.logger
        assert type(litestar_logger) is logging_module.Logger
        assert litestar_logger.name == "litestar"
        assert type(litestar_logger.handlers[0]) is expected_handler_class

        # same handler instance
        assert root_logger.handlers[0] is litestar_logger.handlers[0]


@pytest.mark.parametrize(
    "handlers, expected_handler_class",
    [
        [default_handlers, QueueHandler if sys.version_info >= (3, 12, 0) else StandardQueueListenerHandler],
        [default_picologging_handlers, PicologgingQueueListenerHandler],
    ],
)
def test_connection_logger(handlers: Any, expected_handler_class: Any) -> None:
    @get("/")
    def handler(request: Request) -> Dict[str, bool]:
        return {"isinstance": isinstance(request.logger.handlers[0], expected_handler_class)}  # type: ignore[attr-defined]

    with create_test_client(route_handlers=[handler], logging_config=LoggingConfig(handlers=handlers)) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.json()["isinstance"]


@pytest.mark.parametrize("logging_module", [logging, picologging])
def test_validation(logging_module: ModuleType) -> None:
    with patch("litestar.logging.config.find_spec") as find_spec_mock:
        find_spec_mock.return_value = None if logging_module is logging else True
        logging_config = LoggingConfig(
            formatters={},
            handlers={},
            loggers={},
        )
        default_handlers = _get_default_handlers()

    assert logging_config.formatters["standard"]
    assert len(logging_config.formatters) == 1

    assert logging_config.handlers["queue_listener"] == default_handlers["queue_listener"]
    assert logging_config.handlers["console"] == default_handlers["console"]
    assert len(logging_config.handlers) == 2

    assert logging_config.loggers["litestar"]
    assert logging_config.loggers["litestar"]["handlers"] == ["queue_listener"]
    assert len(logging_config.loggers) == 1


@pytest.mark.parametrize(
    "logging_module, handlers, expected_handler_class",
    [
        [logging, default_handlers, QueueHandler if sys.version_info >= (3, 12, 0) else StandardQueueListenerHandler],
        [picologging, default_picologging_handlers, PicologgingQueueListenerHandler],
    ],
)
def test_root_logger(logging_module: ModuleType, handlers: Any, expected_handler_class: Any) -> None:
    logging_config = LoggingConfig(handlers=handlers)
    get_logger = logging_config.configure()
    root_logger = get_logger()
    assert root_logger.name == "root"  # type: ignore[attr-defined]
    assert isinstance(root_logger, logging_module.Logger)
    root_logger_handler = root_logger.handlers[0]  # pyright: ignore[reportGeneralTypeIssues]
    assert root_logger_handler.name == "queue_listener"
    assert isinstance(root_logger_handler, expected_handler_class)


@pytest.mark.parametrize(
    "logging_module, handlers",
    [
        [logging, default_handlers],
        [picologging, default_picologging_handlers],
    ],
)
def test_root_logger_no_config(logging_module: ModuleType, handlers: Any) -> None:
    logging_config = LoggingConfig(handlers=handlers, configure_root_logger=False)
    get_logger = logging_config.configure()
    root_logger = get_logger()

    assert isinstance(root_logger, logging_module.Logger)

    handlers = root_logger.handlers  # pyright: ignore[reportGeneralTypeIssues]
    if logging_module == logging:
        # pytest automatically configures some handlers
        for handler in handlers:
            assert isinstance(handler, (_LiveLoggingNullHandler, LogCaptureHandler))
    else:
        assert len(handlers) == 0


@pytest.mark.parametrize(
    "logging_module, configure_root_logger, expected_root_logger_handler_class",
    [
        [logging, True, QueueHandler if sys.version_info >= (3, 12, 0) else StandardQueueListenerHandler],
        [logging, False, None],
        [picologging, True, PicologgingQueueListenerHandler],
        [picologging, False, None],
    ],
)
def test_customizing_handler(
    logging_module: ModuleType,
    configure_root_logger: bool,
    expected_root_logger_handler_class: Any,
    capsys: "CaptureFixture[str]",
) -> None:
    log_format = "%(levelname)s :: %(name)s :: %(message)s"

    with patch("litestar.logging.config.find_spec") as find_spec_mock:
        find_spec_mock.return_value = True if logging_module == picologging else None

        logging_config = LoggingConfig(
            formatters={
                "standard": {"format": log_format},
            },
            handlers={
                "console_stdout": {
                    "class": f"{logging_module.__name__}.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "level": "DEBUG",
                    "formatter": "standard",
                },
            },
            loggers={
                "test_logger": {
                    "level": "DEBUG",
                    "handlers": ["console_stdout"],
                    "propagate": False,
                },
                "litestar": {
                    "level": "DEBUG",
                    "handlers": ["console_stdout"],
                    "propagate": False,
                },
            },
            configure_root_logger=configure_root_logger,
        )

        # picologging seems to be broken, cannot make it log on stdout?
        # https://github.com/microsoft/picologging/issues/205
        if logging_module == picologging:
            del logging_config.handlers["console_stdout"]["stream"]

        get_logger = logging_config.configure()

    root_logger = get_logger()

    if configure_root_logger is True:
        assert isinstance(root_logger, logging_module.Logger)
        assert root_logger.level == logging_module.INFO  # pyright: ignore[reportGeneralTypeIssues]

        root_logger_handler = root_logger.handlers[0]  # pyright: ignore[reportGeneralTypeIssues]
        assert root_logger_handler.name == "queue_listener"
        assert type(root_logger_handler) is expected_root_logger_handler_class

        if type(root_logger_handler) is QueueHandler:
            formatter = root_logger_handler.listener.handlers[0].formatter  # type: ignore[attr-defined]
        else:
            formatter = root_logger_handler.formatter
        assert formatter._fmt == log_format
    else:
        # Root logger shouldn't be configured but pytest adds some handlers (for the standard `logging` module)
        for handler in root_logger.handlers:  # type: ignore[attr-defined]
            assert isinstance(handler, (_LiveLoggingNullHandler, LogCaptureHandler))

    def assert_logger(logger: Any) -> None:
        assert type(logger) is logging_module.Logger
        assert logger.level == logging_module.DEBUG
        assert len(logger.handlers) == 1
        assert type(logger.handlers[0]) is logging_module.StreamHandler
        assert logger.handlers[0].name == "console_stdout"
        assert logger.handlers[0].formatter._fmt == log_format

        logger.info("Hello from '%s'", logging_module.__name__)
        if logging_module == picologging:
            log_output = capsys.readouterr().err.strip()
        else:
            log_output = capsys.readouterr().out.strip()
        assert log_output == f"INFO :: {logger.name} :: Hello from '{logging_module.__name__}'"

    assert_logger(get_logger("litestar"))
    assert_logger(get_logger("test_logger"))


def test_excluded_fields() -> None:
    # according to https://docs.python.org/3/library/logging.config.html#dictionary-schema-details
    allowed_fields = {
        "version",
        "formatters",
        "filters",
        "handlers",
        "loggers",
        "root",
        "incremental",
        "disable_existing_loggers",
    }
    with patch("litestar.logging.config.find_spec") as find_spec_mock:
        find_spec_mock.return_value = None

        with patch("logging.config.dictConfig") as dict_config_mock:
            LoggingConfig().configure()
            assert dict_config_mock.called
            for key in dict_config_mock.call_args.args[0].keys():
                assert key in allowed_fields


@pytest.mark.parametrize(
    "traceback_line_limit, expected_warning_deprecation_called",
    [
        [-1, False],
        [20, True],
    ],
)
def test_traceback_line_limit_deprecation(traceback_line_limit: int, expected_warning_deprecation_called: bool) -> None:
    with patch("litestar.logging.config.warn_deprecation") as mock_warning_deprecation:
        LoggingConfig(traceback_line_limit=traceback_line_limit)
        assert mock_warning_deprecation.called is expected_warning_deprecation_called
