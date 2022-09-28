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
