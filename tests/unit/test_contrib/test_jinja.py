# ruff: noqa: F401
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


def test_deprecated_jinja_imports() -> None:
    purge_module(["litestar.contrib.jinja"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing JinjaTemplateEngine from 'litestar.contrib.jinja' is deprecated",
    ):
        from litestar.contrib.jinja import JinjaTemplateEngine


def test_contrib_imports_resolve_to_plugin_objects() -> None:
    purge_module(["litestar.contrib.jinja"], __file__)
    with pytest.warns(DeprecationWarning):
        from litestar.contrib.jinja import JinjaTemplateEngine as ContribJinjaTemplateEngine

    from litestar.plugins.jinja import JinjaTemplateEngine

    assert ContribJinjaTemplateEngine is JinjaTemplateEngine


def test_deprecated_jinja_import_message_includes_version_and_removal() -> None:
    purge_module(["litestar.contrib.jinja"], __file__)
    with pytest.warns(DeprecationWarning) as warning_records:
        from litestar.contrib.jinja import JinjaTemplateEngine

    message = str(warning_records[0].message)
    assert "litestar.contrib.jinja.JinjaTemplateEngine" in message
    assert "Deprecated in litestar 2.22.0" in message
    assert "removed in 3.0.0" in message
    assert "litestar.plugins.jinja" in message


def test_unknown_attribute_raises_attribute_error() -> None:
    purge_module(["litestar.contrib.jinja"], __file__)
    import litestar.contrib.jinja as contrib_jinja

    with pytest.raises(AttributeError):
        contrib_jinja.Nope
