import logging
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

from pydantic import Extra

from starlite import Starlite, get
from starlite.logging import LoggingConfig, LoggingMiddleware
from starlite.testing import TestClient, create_test_client

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from starlette.types import Receive, Scope, Send


@patch("logging.config.dictConfig")
def test_logging_debug(dict_config_mock: Mock) -> None:
    config = LoggingConfig()
    config.configure()
    assert dict_config_mock.mock_calls[0][1][0]["loggers"]["starlite"]["level"] == "INFO"
    dict_config_mock.reset_mock()


@patch("logging.config.dictConfig")
def test_logging_startup(dict_config_mock: Mock) -> None:
    logger = LoggingConfig(loggers={"app": {"level": "INFO", "handlers": ["console"]}})
    with create_test_client([], on_startup=[logger.configure]):
        assert dict_config_mock.called


config = LoggingConfig()
config.configure()
logger = logging.getLogger()


def test_queue_logger(caplog: "LogCaptureFixture") -> None:
    """Test to check logging output contains the logged message."""
    with caplog.at_level(logging.INFO):
        logger.info("Testing now!")
        assert "Testing now!" in caplog.text


def test_logger_startup(caplog: "LogCaptureFixture") -> None:
    with TestClient(app=Starlite(route_handlers=[], on_startup=[LoggingConfig().configure])) as client, caplog.at_level(
        logging.INFO
    ):
        client.options("/")
        logger = logging.getLogger()
        handlers = logger.handlers
        assert isinstance(handlers[0].handlers[0], logging.StreamHandler)  # type: ignore


def test_middleware_config_options() -> None:
    """Should not raise ValidationError."""

    class MyLoggingMiddleware(LoggingMiddleware):
        pass

    class TestLoggingConfig(LoggingConfig, extra=Extra.forbid):
        pass

    TestLoggingConfig(
        middleware_logger_name="another.name.for.logger",
        middleware_log_request=False,
        middleware_log_response=False,
        middleware_class=MyLoggingMiddleware,
    )
    assert True


# MIDLLEWARE TESTS


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


@get(path="/")
def get_handler() -> None:
    return None


@patch("starlite.logging.LoggingMiddleware.get_logger")
def test_middleware_successful_flow(logger_mock: Mock) -> None:
    with create_test_client(route_handlers=[get_handler], middleware=[LoggingConfig().middleware]) as client:
        client.get("/")
        assert logger_mock.call_count == 1
        assert len(logger_mock.mock_calls) == 3
        assert str(logger_mock.mock_calls[1]).startswith("call().info")
        assert "incoming" in str(logger_mock.mock_calls[1])


def test_middleware_config_middleware_class() -> None:
    """Use of a custom middleware."""

    class MyLoggingMiddleware(LoggingMiddleware):
        pass

    config = LoggingConfig(
        middleware_class=MyLoggingMiddleware,
    )
    assert issubclass(type(config.middleware(app=mock_asgi_app)), LoggingMiddleware)
    assert isinstance(config.middleware(app=mock_asgi_app), MyLoggingMiddleware)


@patch("starlite.logging.LoggingMiddleware.get_logger")
def test_middleware_config_middleware_log_request(logger_mock: Mock) -> None:
    """Check that we can logging request."""
    config = LoggingConfig(
        middleware_log_request=False,
    )
    with create_test_client(route_handlers=[get_handler], middleware=[config.middleware]) as client:
        client.get("/")
        assert len(logger_mock.mock_calls) == 2
        assert "incoming" not in logger_mock.mock_calls[1][1][0]


@patch("starlite.logging.LoggingMiddleware.get_logger")
def test_middleware_config_middleware_log_response(logger_mock: Mock) -> None:
    """Check we can stop mlogging response."""
    config = LoggingConfig(
        middleware_log_response=False,
    )
    with create_test_client(route_handlers=[get_handler], middleware=[config.middleware]) as client:
        client.get("/")
        assert len(logger_mock.mock_calls) == 2
        assert "incoming" in logger_mock.mock_calls[1][1][0]


@patch("logging.getLogger")
def test_middleware_config_middleware_logger_name(logger_mock: Mock) -> None:
    """Check we can change logger name."""
    name = "my.ubber.name"
    config = LoggingConfig(
        middleware_logger_name=name,
    )
    middle = config.middleware(app=mock_asgi_app)
    assert getattr(middle, "logger").name == name
