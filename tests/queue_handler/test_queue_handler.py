import logging
from logging import StreamHandler

from _pytest.logging import LogCaptureFixture

from starlite.logging import LoggingConfig

config = LoggingConfig(root={"handlers": ["queue_listener"], "level": "WARNING"})
config.configure()
logger = logging.getLogger()


def test_logger(caplog: LogCaptureFixture) -> None:
    """
    Test to check logging output contains the logged message
    """
    caplog.set_level(logging.INFO)
    logger.info("Testing now!")
    assert "Testing now!" in caplog.text


def test_resolve_handler() -> None:
    """
    Tests resolve handler
    """
    handlers = logger.handlers
    assert isinstance(handlers[0].handlers[0], StreamHandler)  # type: ignore
