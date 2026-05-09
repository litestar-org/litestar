from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mako.lookup import TemplateLookup

from litestar.exceptions import ImproperlyConfiguredException, TemplateNotFoundException
from litestar.plugins.mako import MakoTemplate, MakoTemplateEngine

if TYPE_CHECKING:
    from pathlib import Path


def test_mako_template_engine_instantiation_error(tmp_path: Path) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        MakoTemplateEngine(directory=tmp_path, engine_instance=TemplateLookup(directories=[str(tmp_path)]))


def test_mako_template_engine_instantiated_with_directory(tmp_path: Path) -> None:
    engine = MakoTemplateEngine(directory=tmp_path)
    assert isinstance(engine.engine, TemplateLookup)


def test_mako_template_engine_instantiated_with_engine(tmp_path: Path) -> None:
    lookup = TemplateLookup(directories=[str(tmp_path)])
    engine = MakoTemplateEngine(engine_instance=lookup)
    assert engine.engine is lookup


def test_mako_template_engine_from_template_lookup(tmp_path: Path) -> None:
    lookup = TemplateLookup(directories=[str(tmp_path)])
    engine = MakoTemplateEngine.from_template_lookup(lookup)
    assert engine.engine is lookup


def test_mako_render_string() -> None:
    engine = MakoTemplateEngine(engine_instance=TemplateLookup())
    out = engine.render_string("hello ${name}", {"name": "world"})
    assert out == "hello world"


def test_mako_get_template_raises_template_not_found(tmp_path: Path) -> None:
    engine = MakoTemplateEngine(directory=tmp_path)
    with pytest.raises(TemplateNotFoundException):
        engine.get_template("missing.html")


def test_mako_get_template_returns_template(tmp_path: Path) -> None:
    (tmp_path / "hi.html").write_text("hi ${name}")
    engine = MakoTemplateEngine(directory=tmp_path)
    template = engine.get_template("hi.html")
    assert isinstance(template, MakoTemplate)
    assert template.render(name="xyz") == "hi xyz"


def test_mako_register_template_callable_threads_callable_through_render(tmp_path: Path) -> None:
    engine = MakoTemplateEngine(directory=tmp_path)

    def shouter(context: object, value: str) -> str:
        return value.upper()

    engine.register_template_callable(key="shout", template_callable=shouter)
    (tmp_path / "shout.html").write_text("${shout('hi')}")
    template = engine.get_template("shout.html")
    assert template.render() == "HI"
