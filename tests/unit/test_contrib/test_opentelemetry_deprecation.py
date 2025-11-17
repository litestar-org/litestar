"""Tests for litestar.contrib.opentelemetry deprecation."""

from __future__ import annotations

import pytest


def test_contrib_opentelemetry_module_deprecation() -> None:
    """Test that importing from litestar.contrib.opentelemetry emits deprecation warning."""
    with pytest.warns(
        DeprecationWarning, match=r"litestar\.contrib\.opentelemetry.*deprecated.*litestar\.plugins\.opentelemetry"
    ):
        import litestar.contrib.opentelemetry  # noqa: F401


def test_contrib_opentelemetry_config_deprecation() -> None:
    """Test that importing OpenTelemetryConfig from contrib emits deprecation warning."""
    with pytest.warns(DeprecationWarning, match=r"OpenTelemetryConfig.*deprecated"):
        from litestar.contrib.opentelemetry import OpenTelemetryConfig  # noqa: F401


def test_contrib_opentelemetry_middleware_deprecation() -> None:
    """Test that importing OpenTelemetryInstrumentationMiddleware from contrib emits deprecation warning."""
    with pytest.warns(DeprecationWarning, match=r"OpenTelemetryInstrumentationMiddleware.*deprecated"):
        from litestar.contrib.opentelemetry import OpenTelemetryInstrumentationMiddleware  # noqa: F401


def test_contrib_opentelemetry_plugin_deprecation() -> None:
    """Test that importing OpenTelemetryPlugin from contrib emits deprecation warning."""
    with pytest.warns(DeprecationWarning, match=r"OpenTelemetryPlugin.*deprecated"):
        from litestar.contrib.opentelemetry import OpenTelemetryPlugin  # noqa: F401


def test_plugins_opentelemetry_no_warning() -> None:
    """Test that importing from litestar.plugins.opentelemetry does NOT emit warnings."""
    import warnings

    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")
        from litestar.plugins.opentelemetry import (  # noqa: F401
            OpenTelemetryConfig,
            OpenTelemetryInstrumentationMiddleware,
            OpenTelemetryPlugin,
        )

    # Filter out warnings that are not DeprecationWarning
    deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation_warnings) == 0, (
        "No deprecation warnings should be emitted from litestar.plugins.opentelemetry"
    )


def test_functional_equivalence() -> None:
    """Test that deprecated and new imports provide the same classes."""
    # Note: The module-level deprecation warning already fired in previous tests
    # This test verifies functional equivalence only
    from litestar.contrib.opentelemetry import OpenTelemetryPlugin as DeprecatedPlugin
    from litestar.plugins.opentelemetry import OpenTelemetryPlugin as NewPlugin

    assert DeprecatedPlugin is NewPlugin, "Deprecated and new imports should provide the same class"
