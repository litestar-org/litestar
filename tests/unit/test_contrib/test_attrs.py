from __future__ import annotations

import sys
import warnings
from importlib.util import cache_from_source
from pathlib import Path

import pytest

from litestar.contrib import attrs as contrib_attrs
from litestar.plugins import attrs as plugin_attrs


def purge_module(module_names: list[str], path: str | Path) -> None:
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(cache_from_source(str(path))).unlink(missing_ok=True)


def test_contrib_attrs_deprecation_warning() -> None:
    """Test that importing from contrib.attrs raises a deprecation warning."""
    purge_module(["litestar.contrib.attrs"], __file__)
    with pytest.warns(DeprecationWarning) as warning_info:
        from litestar.contrib.attrs import AttrsSchemaPlugin  # noqa: F401

    assert len(warning_info) == 1
    assert "litestar.contrib.attrs" in str(warning_info[0].message)
    assert "Please use 'litestar.plugins.attrs' instead" in str(warning_info[0].message)


def test_plugin_attrs_no_warning() -> None:
    """Test that importing from plugins.attrs does not raise a deprecation warning."""
    purge_module(["litestar.plugins.attrs"], __file__)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        from litestar.plugins.attrs import AttrsSchemaPlugin  # noqa: F401


def test_functionality_parity() -> None:
    """Test that the functionality is identical between contrib and plugin versions."""
    assert contrib_attrs.AttrsSchemaPlugin is plugin_attrs.AttrsSchemaPlugin
    assert contrib_attrs.is_attrs_class is plugin_attrs.is_attrs_class
