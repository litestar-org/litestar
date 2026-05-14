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


@pytest.mark.parametrize("attr_name", ("MakoTemplate", "MakoTemplateEngine"))
def test_deprecated_mako_imports(attr_name: str) -> None:
    purge_module(["litestar.contrib.mako"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match=f"importing {attr_name} from 'litestar.contrib.mako' is deprecated",
    ):
        exec(f"from litestar.contrib.mako import {attr_name}", {})


def test_contrib_imports_resolve_to_plugin_objects() -> None:
    purge_module(["litestar.contrib.mako"], __file__)
    with pytest.warns(DeprecationWarning):
        from litestar.contrib.mako import MakoTemplate as ContribMakoTemplate
        from litestar.contrib.mako import MakoTemplateEngine as ContribMakoTemplateEngine

    from litestar.plugins.mako import MakoTemplate, MakoTemplateEngine

    assert ContribMakoTemplate is MakoTemplate
    assert ContribMakoTemplateEngine is MakoTemplateEngine


def test_deprecated_mako_import_message_includes_version_and_removal() -> None:
    purge_module(["litestar.contrib.mako"], __file__)
    with pytest.warns(DeprecationWarning) as warning_records:
        from litestar.contrib.mako import MakoTemplateEngine

    message = str(warning_records[0].message)
    assert "litestar.contrib.mako.MakoTemplateEngine" in message
    assert "Deprecated in litestar 2.22.0" in message
    assert "removed in 3.0.0" in message
    assert "litestar.plugins.mako" in message


def test_unknown_attribute_raises_attribute_error() -> None:
    purge_module(["litestar.contrib.mako"], __file__)
    import litestar.contrib.mako as contrib_mako

    with pytest.raises(AttributeError):
        contrib_mako.Nope
