from __future__ import annotations

import sys
from importlib.util import cache_from_source
from pathlib import Path

import pytest
from minijinja import Environment

from litestar.exceptions import ImproperlyConfiguredException, TemplateNotFoundException
from litestar.plugins.minijinja import MiniJinjaTemplateEngine


def purge_module(module_names: list[str], path: str | Path) -> None:
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(cache_from_source(str(path))).unlink(missing_ok=True)


def test_mini_jinja_template_engine_instantiation_error(tmp_path: Path) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        MiniJinjaTemplateEngine(directory=tmp_path, engine_instance=Environment())

    with pytest.raises(ImproperlyConfiguredException):
        MiniJinjaTemplateEngine()


def test_mini_jinja_template_engine_instantiated_with_engine() -> None:
    engine = Environment()
    template_engine = MiniJinjaTemplateEngine(engine_instance=engine)
    assert template_engine.engine is engine


def test_mini_jinja_template_render_raises_template_not_found(tmp_path: Path) -> None:
    template_engine = MiniJinjaTemplateEngine(engine_instance=Environment())
    with pytest.raises(TemplateNotFoundException):
        tmpl = template_engine.get_template("not_found.html")
        tmpl.render()


def test_mini_jinja_template_render_string(tmp_path: Path) -> None:
    template_engine = MiniJinjaTemplateEngine(engine_instance=Environment())

    good_template = template_engine.render_string("template as a {{value}}", context={"value": "string"})
    assert good_template == "template as a string"


def test_from_environment() -> None:
    engine = Environment()
    template_engine = MiniJinjaTemplateEngine.from_environment(engine)
    assert template_engine.engine is engine


@pytest.mark.parametrize(
    "attr_name",
    ("MiniJinjaTemplateEngine", "StateProtocol", "MiniJinjaTemplate", "_transform_state"),
)
def test_deprecated_minijinja_imports(attr_name: str) -> None:
    purge_module(["litestar.contrib.minijinja"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match=f"importing {attr_name} from 'litestar.contrib.minijinja' is deprecated",
    ):
        exec(f"from litestar.contrib.minijinja import {attr_name}", {})


def test_contrib_imports_resolve_to_plugin_objects() -> None:
    purge_module(["litestar.contrib.minijinja"], __file__)
    with pytest.warns(DeprecationWarning):
        from litestar.contrib.minijinja import MiniJinjaTemplateEngine as ContribMiniJinjaTemplateEngine
        from litestar.contrib.minijinja import StateProtocol as ContribStateProtocol
        from litestar.contrib.minijinja import _transform_state as contrib_transform_state

    from litestar.plugins.minijinja import StateProtocol, _transform_state

    assert ContribMiniJinjaTemplateEngine is MiniJinjaTemplateEngine
    assert ContribStateProtocol is StateProtocol
    assert contrib_transform_state is _transform_state


def test_deprecated_minijinja_import_message_includes_version_and_removal() -> None:
    purge_module(["litestar.contrib.minijinja"], __file__)
    with pytest.warns(DeprecationWarning) as warning_records:
        from litestar.contrib.minijinja import MiniJinjaTemplateEngine as ContribMiniJinjaTemplateEngine

    message = str(warning_records[0].message)
    assert ContribMiniJinjaTemplateEngine is MiniJinjaTemplateEngine
    assert "litestar.contrib.minijinja.MiniJinjaTemplateEngine" in message
    assert "Deprecated in litestar 2.22.0" in message
    assert "removed in 3.0.0" in message
    assert "litestar.plugins.minijinja" in message


def test_existing_minijinja_from_state_deprecation_still_resolves() -> None:
    purge_module(["litestar.contrib.minijinja"], __file__)
    with pytest.warns(DeprecationWarning, match="minijinja_from_state"):
        from litestar.contrib.minijinja import minijinja_from_state

    from litestar.plugins.minijinja import _minijinja_from_state

    assert minijinja_from_state is _minijinja_from_state


def test_unknown_attribute_raises_attribute_error() -> None:
    purge_module(["litestar.contrib.minijinja"], __file__)
    import litestar.contrib.minijinja as contrib_minijinja

    with pytest.raises(AttributeError):
        contrib_minijinja.Nope
