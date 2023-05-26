from __future__ import annotations

import logging

import pytest
from _pytest.monkeypatch import MonkeyPatch

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


@pytest.mark.parametrize("env_name,app_attr", [("LITESTAR_DEBUG", "debug"), ("LITESTAR_PDB", "pdb_on_exception")])
@pytest.mark.parametrize(
    "env_value,app_value,expected_value",
    [
        (None, None, False),
        (None, False, False),
        (None, True, True),
        ("0", None, False),
        ("0", False, False),
        ("0", True, True),
        ("1", None, True),
        ("1", False, False),
        ("1", True, True),
    ],
)
def test_set_env_flags(
    monkeypatch: MonkeyPatch,
    env_value: str | None,
    app_value: bool | None,
    expected_value: bool,
    env_name: str,
    app_attr: str,
) -> None:
    if env_value is not None:
        monkeypatch.setenv(env_name, env_value)
    else:
        monkeypatch.delenv(env_name, raising=False)

    app = Litestar(**{app_attr: app_value})  # type: ignore[arg-type]

    assert getattr(app, app_attr) is expected_value
