from pytest import CaptureFixture
from structlog.processors import JSONRenderer
from structlog.types import BindableLogger

from litestar.logging.config import StructLoggingConfig, default_json_serializer
from litestar.serialization import decode_json
from litestar.testing import create_test_client

# structlog.testing.capture_logs changes the processors
# Because we want to test processors, use capsys instead


def test_structlog_config_default(capsys: CaptureFixture) -> None:
    with create_test_client([], logging_config=StructLoggingConfig()) as client:
        assert client.app.logger
        assert isinstance(client.app.logger.bind(), BindableLogger)
        client.app.logger.info("message", key="value")

        log_messages = [decode_json(value=x) for x in capsys.readouterr().out.splitlines()]
        assert len(log_messages) == 1

        # Format should be: {event: message, key: value, level: info, timestamp: isoformat}
        log_messages[0].pop("timestamp")  # Assume structlog formats timestamp correctly
        assert log_messages[0] == {"event": "message", "key": "value", "level": "info"}


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
