import logging
from typing import TYPE_CHECKING

from examples.application_hooks import after_exception_hook
from litestar.testing import TestClient

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


def test_application_shutdown_hooks(caplog: "LogCaptureFixture") -> None:
    with caplog.at_level(logging.INFO), TestClient(app=after_exception_hook.app) as client:
        assert len(caplog.messages) == 0
        client.get("/some-path")
        assert client.app.state.error_count == 1
        assert len(caplog.messages) == 1
        client.get("/some-path")
        assert client.app.state.error_count == 2
        assert len(caplog.messages) == 2
