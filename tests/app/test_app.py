from __future__ import annotations

import logging

import pytest

from litestar import Litestar
from litestar.exceptions import ImproperlyConfiguredException


def test_access_openapi_schema_raises_if_not_configured() -> None:
    """Test that accessing the openapi schema raises if not configured."""
    app = Litestar(openapi_config=None)
    with pytest.raises(ImproperlyConfiguredException):
        app.openapi_schema


def test_set_debug_updates_logging_level() -> None:
    app = Litestar()

    assert app.logger is not None
    assert app.logger.level == logging.INFO  # type: ignore[attr-defined]

    app.debug = True
    assert app.logger.level == logging.DEBUG  # type: ignore[attr-defined]

    app.debug = False
    assert app.logger.level == logging.INFO  # type: ignore[attr-defined]
