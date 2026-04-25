# ruff: noqa: F401
import importlib
import sys
from importlib.util import cache_from_source
from pathlib import Path
from typing import Union

import pytest


def purge_module(module_names: "list[str]", path: "Union[str, Path]") -> None:
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(cache_from_source(str(path))).unlink(missing_ok=True)


def test_deprecated_opentelemetry_imports() -> None:
    purge_module(["litestar.contrib.opentelemetry"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing OpenTelemetryConfig from 'litestar.contrib.opentelemetry' is deprecated",
    ):
        from litestar.contrib.opentelemetry import OpenTelemetryConfig

    purge_module(["litestar.contrib.opentelemetry"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing OpenTelemetryInstrumentationMiddleware from 'litestar.contrib.opentelemetry' is deprecated",
    ):
        from litestar.contrib.opentelemetry import OpenTelemetryInstrumentationMiddleware

    purge_module(["litestar.contrib.opentelemetry"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing OpenTelemetryPlugin from 'litestar.contrib.opentelemetry' is deprecated",
    ):
        from litestar.contrib.opentelemetry import OpenTelemetryPlugin


def test_deprecated_opentelemetry_config_imports() -> None:
    purge_module(["litestar.contrib.opentelemetry.config"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing OpenTelemetryConfig from 'litestar.contrib.opentelemetry.config' is deprecated",
    ):
        from litestar.contrib.opentelemetry.config import OpenTelemetryConfig


def test_deprecated_opentelemetry_middleware_imports() -> None:
    purge_module(["litestar.contrib.opentelemetry.middleware"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing OpenTelemetryInstrumentationMiddleware from 'litestar.contrib.opentelemetry.middleware' is deprecated",
    ):
        from litestar.contrib.opentelemetry.middleware import OpenTelemetryInstrumentationMiddleware


def test_deprecated_opentelemetry_plugin_imports() -> None:
    purge_module(["litestar.contrib.opentelemetry.plugin"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing OpenTelemetryPlugin from 'litestar.contrib.opentelemetry.plugin' is deprecated",
    ):
        from litestar.contrib.opentelemetry.plugin import OpenTelemetryPlugin


def test_contrib_imports_resolve_to_plugin_objects() -> None:
    """Sanity check: deprecated symbols are the same object as the plugin location."""
    purge_module(["litestar.contrib.opentelemetry"], __file__)
    with pytest.warns(DeprecationWarning):
        from litestar.contrib.opentelemetry import (
            OpenTelemetryConfig as ContribConfig,
        )
        from litestar.contrib.opentelemetry import (
            OpenTelemetryInstrumentationMiddleware as ContribMiddleware,
        )
        from litestar.contrib.opentelemetry import (
            OpenTelemetryPlugin as ContribPlugin,
        )

    from litestar.plugins.opentelemetry import (
        OpenTelemetryConfig,
        OpenTelemetryInstrumentationMiddleware,
        OpenTelemetryPlugin,
    )

    assert ContribConfig is OpenTelemetryConfig
    assert ContribMiddleware is OpenTelemetryInstrumentationMiddleware
    assert ContribPlugin is OpenTelemetryPlugin
