import pytest

from starlite.contrib import jinja, mako


def test_deprecated_jinja_engine_export() -> None:
    with pytest.deprecated_call():
        from starlite.template import JinjaTemplateEngine

    assert JinjaTemplateEngine is jinja.JinjaTemplateEngine


def test_deprecated_mako_engine_export() -> None:
    with pytest.deprecated_call():
        from starlite.template import MakoTemplateEngine

    assert MakoTemplateEngine is mako.MakoTemplateEngine


def test_deprecated_mako_template_export() -> None:
    with pytest.deprecated_call():
        from starlite.template import MakoTemplate

    assert MakoTemplate is mako.MakoTemplate


def test_raises_for_unknown_module() -> None:
    with pytest.raises(ImportError):
        from starlite.template import MyTemplate  # noqa
