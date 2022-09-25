from structlog._config import BoundLoggerLazyProxy

from starlite.config import StructLoggingConfig
from starlite.testing import create_test_client


def test_structlog_config() -> None:
    with create_test_client([], logging_config=StructLoggingConfig()) as client:
        assert isinstance(client.app.logger, BoundLoggerLazyProxy)
