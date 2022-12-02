from structlog.processors import JSONRenderer
from structlog.testing import capture_logs
from structlog.types import BindableLogger

from starlite.config import StructLoggingConfig
from starlite.testing import create_test_client


def test_structlog_config() -> None:
    with create_test_client([], logging_config=StructLoggingConfig()) as client, capture_logs() as cap_logs:
        assert client.app.logger
        assert isinstance(client.app.logger, BindableLogger)
        client.app.logger.info("message", key="value")
        assert len(cap_logs) == 1
        assert cap_logs[0] == {"key": "value", "event": "message", "log_level": "info"}


def test_structlog_config_specify_processors() -> None:
    logging_config = StructLoggingConfig(processors=[JSONRenderer()])

    with create_test_client([], logging_config=logging_config) as client, capture_logs() as cap_logs:
        assert client.app.logger
        assert isinstance(client.app.logger, BindableLogger)

        client.app.logger.info("message1", key="value1")
        assert len(cap_logs) == 1
        assert cap_logs[0] == {"key": "value1", "event": "message1", "log_level": "info"}

        # Log twice to make sure issue #882 doesn't appear again
        client.app.logger.info("message2", key="value2")
        assert len(cap_logs) == 2
        assert cap_logs[1] == {"key": "value2", "event": "message2", "log_level": "info"}
