# ruff: noqa: TC004, F401
from __future__ import annotations

import importlib
import sys
from importlib.util import cache_from_source
from pathlib import Path

import pytest


def purge_module(module_names: list[str], path: str | Path) -> None:
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(cache_from_source(str(path))).unlink(missing_ok=True)


def test_deprecated_prometheus_imports() -> None:
    purge_module(["litestar.contrib.prometheus"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing PrometheusMiddleware from 'litestar.contrib.prometheus' is deprecated"
    ):
        from litestar.contrib.prometheus import PrometheusMiddleware

    purge_module(["litestar.contrib.prometheus"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing PrometheusConfig from 'litestar.contrib.prometheus' is deprecated"
    ):
        from litestar.contrib.prometheus import PrometheusConfig

    purge_module(["litestar.contrib.prometheus"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing PrometheusController from 'litestar.contrib.prometheus' is deprecated"
    ):
        from litestar.contrib.prometheus import PrometheusController


def test_deprecated_prometheus_middleware_imports() -> None:
    purge_module(["litestar.contrib.prometheus.middleware"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing PrometheusMiddleware from 'litestar.contrib.prometheus.middleware' is deprecated",
    ):
        from litestar.contrib.prometheus.middleware import PrometheusMiddleware


def test_deprecated_prometheus_config_imports() -> None:
    purge_module(["litestar.contrib.prometheus.config"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing PrometheusConfig from 'litestar.contrib.prometheus.config' is deprecated",
    ):
        from litestar.contrib.prometheus.config import PrometheusConfig


def test_deprecated_prometheus_controller_imports() -> None:
    purge_module(["litestar.contrib.prometheus.controller"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing PrometheusController from 'litestar.contrib.prometheus.controller' is deprecated",
    ):
        from litestar.contrib.prometheus.controller import PrometheusController
