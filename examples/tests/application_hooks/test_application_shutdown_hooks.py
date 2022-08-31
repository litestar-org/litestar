import logging
from typing import TYPE_CHECKING

from examples.application_hooks import shutdown_hooks
from starlite.testing import TestClient

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


def test_application_shutdown_hooks(caplog: "LogCaptureFixture") -> None:
    with caplog.at_level(logging.INFO), TestClient(app=shutdown_hooks.app):
        assert len(caplog.messages) == 0
    assert len(caplog.messages) == 2
    assert "shutdown sequence begin" in caplog.messages[0]
    assert "shutdown sequence ended" in caplog.messages[1]
