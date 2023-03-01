import logging
from typing import TYPE_CHECKING

from examples.application_hooks import startup_hooks
from starlite.testing import TestClient

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


def test_application_startup_hooks(caplog: "LogCaptureFixture") -> None:
    with caplog.at_level(logging.INFO), TestClient(app=startup_hooks.app):
        assert len(caplog.messages) == 2
        assert "startup sequence begin" in caplog.messages[0]
        assert "startup sequence ended" in caplog.messages[1]
